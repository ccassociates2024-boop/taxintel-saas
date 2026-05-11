from decimal import Decimal

from app.schemas.tax import AisData, CapitalGainsInput, RecommendationRequest, TaxpayerProfile
from app.services.rules import scrutiny_risk


def test_scrutiny_risk_flags_capital_gain_and_remittance_gaps():
    request = RecommendationRequest(
        profile=TaxpayerProfile(residential_status="RESIDENT"),
        ais=AisData(
            capital_gains=Decimal("500000"),
            foreign_remittance=Decimal("650000"),
            high_value_transactions=Decimal("1500000"),
        ),
        capital_gains=CapitalGainsInput(stcg_equity_111a=Decimal("100000")),
    )

    risk = scrutiny_risk(request)

    assert risk.risk_level == "HIGH"
    assert any("capital gains" in trigger.lower() for trigger in risk.triggers)
    assert any("foreign remittance" in trigger.lower() for trigger in risk.triggers)

