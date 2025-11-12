import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.fund import Fund
from app.models.transaction import CapitalCall, Distribution, Adjustment
from app.services.metrics_calculator import MetricsCalculator


def _seed_flows(session: Session) -> int:
    fund = Fund(name="Breakdown Fund")
    session.add(fund)
    session.commit()
    session.refresh(fund)

    session.add_all([
        CapitalCall(fund_id=fund.id, call_date=date(2020, 1, 1), amount=Decimal("100"), description="Initial call"),
        CapitalCall(fund_id=fund.id, call_date=date(2020, 2, 1), amount=Decimal("50"), description="Follow-on"),
        Adjustment(fund_id=fund.id, adjustment_date=date(2020, 3, 1), amount=Decimal("10"), description="Fee"),
        Distribution(fund_id=fund.id, distribution_date=date(2020, 6, 1), amount=Decimal("90"), description="Proceeds"),
        Distribution(fund_id=fund.id, distribution_date=date(2021, 1, 1), amount=Decimal("50"), description="Proceeds"),
    ])
    session.commit()
    return fund.id


def test_breakdown_dpi(db_session: Session):
    fund_id = _seed_flows(db_session)
    calc = MetricsCalculator(db_session)
    breakdown = calc.get_calculation_breakdown(fund_id, metric="dpi")
    assert breakdown["metric"] == "DPI"
    assert breakdown["result"] == calc.calculate_dpi(fund_id)
    assert breakdown["pic"] == float(calc.calculate_pic(fund_id))
    assert len(breakdown["transactions"]["capital_calls"]) == 2
    assert len(breakdown["transactions"]["distributions"]) == 2
    assert len(breakdown["transactions"]["adjustments"]) == 1


def test_breakdown_pic(db_session: Session):
    fund_id = _seed_flows(db_session)
    calc = MetricsCalculator(db_session)
    breakdown = calc.get_calculation_breakdown(fund_id, metric="pic")
    assert breakdown["metric"] == "PIC"
    assert breakdown["result"] == float(calc.calculate_pic(fund_id))
    assert breakdown["total_calls"] == 150.0
    assert breakdown["total_adjustments"] == 10.0
    assert len(breakdown["transactions"]["capital_calls"]) == 2


def test_breakdown_irr(db_session: Session):
    fund_id = _seed_flows(db_session)
    calc = MetricsCalculator(db_session)
    breakdown = calc.get_calculation_breakdown(fund_id, metric="irr")
    assert breakdown["metric"] == "IRR"
    assert breakdown["result"] == calc.calculate_irr(fund_id)
    # Cash flow totals reflect signs (calls negative, dists positive)
    cf_summary = breakdown["cash_flow_summary"]
    assert cf_summary["total_outflows"] < 0
    assert cf_summary["total_inflows"] > 0
    assert len(breakdown["cash_flows"]) >= 4