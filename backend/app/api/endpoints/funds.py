"""
Fund API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.models.fund import Fund
from app.models.transaction import CapitalCall, Distribution, Adjustment
from app.schemas.fund import Fund as FundSchema, FundCreate, FundUpdate, FundMetrics
from app.schemas.transaction import (
    CapitalCall as CapitalCallSchema,
    Distribution as DistributionSchema,
    Adjustment as AdjustmentSchema,
    TransactionList
)
from app.services.metrics_calculator import MetricsCalculator
import pandas as pd
import io

router = APIRouter()


@router.get("/", response_model=List[FundSchema])
async def list_funds(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all funds"""
    funds = db.query(Fund).offset(skip).limit(limit).all()
    
    # Add metrics to each fund
    calculator = MetricsCalculator(db)
    result = []
    
    for fund in funds:
        fund_dict = FundSchema.model_validate(fund).model_dump()
        metrics = calculator.calculate_all_metrics(fund.id)
        fund_dict["metrics"] = FundMetrics(**metrics)
        result.append(FundSchema(**fund_dict))
    
    return result


@router.post("/", response_model=FundSchema)
async def create_fund(fund: FundCreate, db: Session = Depends(get_db)):
    """Create a new fund"""
    db_fund = Fund(**fund.model_dump())
    db.add(db_fund)
    db.commit()
    db.refresh(db_fund)
    return db_fund


@router.get("/{fund_id}", response_model=FundSchema)
async def get_fund(fund_id: int, db: Session = Depends(get_db)):
    """Get fund details"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    # Add metrics
    calculator = MetricsCalculator(db)
    metrics = calculator.calculate_all_metrics(fund_id)
    
    fund_dict = FundSchema.model_validate(fund).model_dump()
    fund_dict["metrics"] = FundMetrics(**metrics)
    
    return FundSchema(**fund_dict)


@router.put("/{fund_id}", response_model=FundSchema)
async def update_fund(
    fund_id: int,
    fund_update: FundUpdate,
    db: Session = Depends(get_db)
):
    """Update fund details"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    update_data = fund_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(fund, key, value)
    
    db.commit()
    db.refresh(fund)
    return fund


@router.delete("/{fund_id}")
async def delete_fund(fund_id: int, db: Session = Depends(get_db)):
    """Delete a fund"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    db.delete(fund)
    db.commit()
    
    return {"message": "Fund deleted successfully"}


@router.get("/{fund_id}/transactions", response_model=TransactionList)
async def get_fund_transactions(
    fund_id: int,
    transaction_type: str = Query(..., regex="^(capital_calls|distributions|adjustments)$"),
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get fund transactions"""
    # Verify fund exists
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    # Query based on transaction type
    if transaction_type == "capital_calls":
        query = db.query(CapitalCall).filter(CapitalCall.fund_id == fund_id)
        model = CapitalCallSchema
    elif transaction_type == "distributions":
        query = db.query(Distribution).filter(Distribution.fund_id == fund_id)
        model = DistributionSchema
    else:  # adjustments
        query = db.query(Adjustment).filter(Adjustment.fund_id == fund_id)
        model = AdjustmentSchema
    
    # Get total count
    total = query.count()
    
    # Paginate
    skip = (page - 1) * limit
    items = query.offset(skip).limit(limit).all()
    
    # Calculate total pages
    pages = (total + limit - 1) // limit
    
    return TransactionList(
        items=[model.model_validate(item) for item in items],
        total=total,
        page=page,
        pages=pages
    )


@router.get("/{fund_id}/metrics", response_model=FundMetrics)
async def get_fund_metrics(fund_id: int, db: Session = Depends(get_db)):
    """Get fund metrics"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    calculator = MetricsCalculator(db)
    metrics = calculator.calculate_all_metrics(fund_id)
    
    return FundMetrics(**metrics)


@router.get("/{fund_id}/export.xlsx")
async def export_fund_excel(
    fund_id: int,
    include: str = Query("all", regex="^(all|transactions|metrics)$"),
    db: Session = Depends(get_db)
):
    """Export fund data to Excel (metrics and/or transactions)"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # Metrics
        if include in ("all", "metrics"):
            calculator = MetricsCalculator(db)
            metrics = calculator.calculate_all_metrics(fund_id)
            metrics_df = pd.DataFrame([
                {"Metric": k, "Value": v} for k, v in metrics.items()
            ])
            metrics_df.to_excel(writer, sheet_name="Metrics", index=False)

        # Transactions
        if include in ("all", "transactions"):
            cc_items = (
                db.query(CapitalCall)
                .filter(CapitalCall.fund_id == fund_id)
                .order_by(CapitalCall.call_date.asc())
                .all()
            )
            cc_df = pd.DataFrame([
                {
                    "ID": c.id,
                    "Date": c.call_date,
                    "Type": c.call_type,
                    "Amount": float(c.amount),
                    "Description": c.description,
                }
                for c in cc_items
            ])
            cc_df.to_excel(writer, sheet_name="Capital Calls", index=False)

            dist_items = (
                db.query(Distribution)
                .filter(Distribution.fund_id == fund_id)
                .order_by(Distribution.distribution_date.asc())
                .all()
            )
            dist_df = pd.DataFrame([
                {
                    "ID": d.id,
                    "Date": d.distribution_date,
                    "Type": d.distribution_type,
                    "Recallable": bool(d.is_recallable),
                    "Amount": float(d.amount),
                    "Description": d.description,
                }
                for d in dist_items
            ])
            dist_df.to_excel(writer, sheet_name="Distributions", index=False)

            adj_items = (
                db.query(Adjustment)
                .filter(Adjustment.fund_id == fund_id)
                .order_by(Adjustment.adjustment_date.asc())
                .all()
            )
            adj_df = pd.DataFrame([
                {
                    "ID": a.id,
                    "Date": a.adjustment_date,
                    "Type": a.adjustment_type,
                    "Category": a.category,
                    "Contribution Adjustment": bool(a.is_contribution_adjustment),
                    "Amount": float(a.amount),
                    "Description": a.description,
                }
                for a in adj_items
            ])
            adj_df.to_excel(writer, sheet_name="Adjustments", index=False)

    buffer.seek(0)
    headers = {
        "Content-Disposition": f"attachment; filename=fund_{fund_id}_export.xlsx"
    }
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
