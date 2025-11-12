import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.fund import Fund
from app.models.transaction import CapitalCall, Distribution, Adjustment
from app.services.metrics_calculator import MetricsCalculator


def _seed_basic_fund(session: Session) -> int:
    fund = Fund(name="Test Fund")
    session.add(fund)
    session.commit()
    session.refresh(fund)
    return fund.id


def test_pic_basic(db_session: Session):
    fund_id = _seed_basic_fund(db_session)
    # Capital calls: 100, 50
    db_session.add_all([
        CapitalCall(fund_id=fund_id, call_date=date(2020, 1, 1), amount=Decimal("100")),
        CapitalCall(fund_id=fund_id, call_date=date(2020, 2, 1), amount=Decimal("50")),
    ])
    # Adjustments: 10
    db_session.add(Adjustment(fund_id=fund_id, adjustment_date=date(2020, 3, 1), amount=Decimal("10")))
    db_session.commit()

    calc = MetricsCalculator(db_session)
    pic = calc.calculate_pic(fund_id)
    assert float(pic) == 140.0  # 100 + 50 - 10


def test_dpi_zero_pic(db_session: Session):
    fund_id = _seed_basic_fund(db_session)
    # No capital calls -> PIC 0, add some distributions
    db_session.add(Distribution(fund_id=fund_id, distribution_date=date(2021, 1, 1), amount=Decimal("25")))
    db_session.commit()

    calc = MetricsCalculator(db_session)
    dpi = calc.calculate_dpi(fund_id)
    assert dpi == 0.0


def test_dpi_with_values(db_session: Session):
    fund_id = _seed_basic_fund(db_session)
    db_session.add_all([
        CapitalCall(fund_id=fund_id, call_date=date(2020, 1, 1), amount=Decimal("200")),
        Adjustment(fund_id=fund_id, adjustment_date=date(2020, 1, 15), amount=Decimal("20")),
        Distribution(fund_id=fund_id, distribution_date=date(2020, 6, 1), amount=Decimal("90")),
    ])
    db_session.commit()

    calc = MetricsCalculator(db_session)
    dpi = calc.calculate_dpi(fund_id)
    # PIC = 180, total distributions = 90 => DPI = 0.5
    assert dpi == 0.5


def test_irr_minimum_flows(db_session: Session):
    fund_id = _seed_basic_fund(db_session)
    # Two flows: -100 then +110 => IRR should be positive
    db_session.add_all([
        CapitalCall(fund_id=fund_id, call_date=date(2020, 1, 1), amount=Decimal("100")),
        Distribution(fund_id=fund_id, distribution_date=date(2021, 1, 1), amount=Decimal("110")),
    ])
    db_session.commit()

    calc = MetricsCalculator(db_session)
    irr = calc.calculate_irr(fund_id)
    assert irr is not None
    assert irr > 0


def test_calculate_all_metrics(db_session: Session):
    fund_id = _seed_basic_fund(db_session)
    db_session.add_all([
        CapitalCall(fund_id=fund_id, call_date=date(2020, 1, 1), amount=Decimal("100")),
        CapitalCall(fund_id=fund_id, call_date=date(2020, 2, 1), amount=Decimal("50")),
        Adjustment(fund_id=fund_id, adjustment_date=date(2020, 3, 1), amount=Decimal("10")),
        Distribution(fund_id=fund_id, distribution_date=date(2020, 6, 1), amount=Decimal("90")),
        Distribution(fund_id=fund_id, distribution_date=date(2021, 1, 1), amount=Decimal("50")),
    ])
    db_session.commit()

    calc = MetricsCalculator(db_session)
    m = calc.calculate_all_metrics(fund_id)
    assert pytest.approx(m["pic"], 0.001) == 140.0
    assert pytest.approx(m["total_distributions"], 0.001) == 140.0
    assert m["dpi"] == 1.0
    assert m["irr"] is None or isinstance(m["irr"], float)