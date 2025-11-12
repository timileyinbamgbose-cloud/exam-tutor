"""
Partnership Management System
ExamsTutor AI - Phase 5: Scale & Growth

Manage strategic partnerships with government, telcos, device manufacturers, and NGOs.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from decimal import Decimal


class PartnerType(str, Enum):
    """Type of partner"""
    GOVERNMENT = "government"
    TELCO = "telco"
    DEVICE_MANUFACTURER = "device_manufacturer"
    NGO = "ngo"
    CORPORATE_SPONSOR = "corporate_sponsor"
    EDUCATIONAL_INSTITUTION = "educational_institution"


class PartnershipStatus(str, Enum):
    """Partnership status"""
    LEAD = "lead"
    IN_DISCUSSION = "in_discussion"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATING = "negotiating"
    CONTRACT_SIGNED = "contract_signed"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


@dataclass
class Partner:
    """Partner organization record"""
    partner_id: str
    name: str
    type: PartnerType
    status: PartnershipStatus

    # Contact information
    contact_name: str
    contact_email: str
    contact_phone: str
    website: Optional[str] = None

    # Partnership details
    partnership_start_date: Optional[datetime] = None
    partnership_end_date: Optional[datetime] = None
    contract_value: Decimal = Decimal('0')

    # Specific details per partner type
    details: Dict[str, Any] = None

    # Tracking
    students_impacted: int = 0
    schools_impacted: int = 0
    total_value_delivered: Decimal = Decimal('0')

    notes: str = ""
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class GovernmentPartner:
    """Government partnership details"""
    partner_id: str
    ministry_name: str
    level: str  # "federal", "state", "local"
    state: Optional[str] = None  # For state-level partnerships

    # Contract details
    contract_type: str  # "pilot", "district_license", "state_wide"
    num_schools: int = 0
    num_students: int = 0
    contract_value_yearly: Decimal = Decimal('0')

    # Terms
    free_tier_provided: bool = True
    training_included: bool = True
    dedicated_support: bool = True
    sla_uptime: str = "99.9%"

    # Reporting
    quarterly_reports_required: bool = True
    impact_assessment_required: bool = True

    # Payment terms
    payment_schedule: str = "annual"  # "monthly", "quarterly", "annual"
    billing_entity: str = ""  # Ministry name for invoicing

    created_at: datetime = None


@dataclass
class TelcoPartner:
    """Telco partnership details"""
    partner_id: str
    telco_name: str  # MTN, Airtel, Glo, 9mobile

    # Data bundle offering
    education_bundle_enabled: bool = False
    bundle_price_ngn: Decimal = Decimal('0')
    bundle_size_gb: int = 0
    discount_percent: int = 0  # Discount from regular price

    # Zero-rating
    zero_rating_enabled: bool = False
    zero_rated_domains: List[str] = None  # ["*.examstutor.ng"]

    # Marketing
    co_marketing_agreement: bool = False
    marketing_budget_ngn: Decimal = Decimal('0')

    # Revenue share
    revenue_share_enabled: bool = False
    revenue_share_percent: int = 0  # % of subscriptions driven by telco

    # Students impacted
    students_using_bundle: int = 0

    created_at: datetime = None


@dataclass
class DevicePartner:
    """Device manufacturer partnership details"""
    partner_id: str
    manufacturer_name: str  # Samsung, Tecno, Infinix, etc.

    # Pre-installation
    app_preinstalled: bool = False
    device_models: List[str] = None

    # Device subsidy program
    subsidy_program_active: bool = False
    subsidy_amount_ngn: Decimal = Decimal('0')  # Per device
    num_subsidized_devices: int = 0

    # Bundled subscription
    bundled_subscription: bool = False
    subscription_duration_months: int = 0  # Free months included

    # Co-branding
    co_branded_devices: bool = False
    education_device_line: bool = False

    # Revenue share
    revenue_share_percent: int = 0  # % of device sales through ExamsTutor

    # Impact
    devices_sold: int = 0
    students_reached: int = 0

    created_at: datetime = None


@dataclass
class NGOSponsor:
    """NGO/Corporate sponsorship details"""
    partner_id: str
    organization_name: str
    organization_type: str  # "ngo", "corporate", "foundation"

    # Sponsorship program
    students_sponsored: int = 0
    sponsorship_per_student_monthly: Decimal = Decimal('0')
    total_monthly_commitment: Decimal = Decimal('0')

    # Targeting criteria
    target_demographics: str = ""  # "rural", "underprivileged", "girls", etc.
    target_regions: List[str] = None
    target_schools: List[str] = None

    # Reporting
    impact_reports_frequency: str = "monthly"  # "weekly", "monthly", "quarterly"
    student_testimonials_required: bool = True
    photo_video_documentation: bool = False

    # Benefits for sponsor
    branding_on_platform: bool = False
    certificates_for_students: bool = True
    tax_deduction_documentation: bool = True
    public_recognition: bool = True

    # Tracking
    total_invested: Decimal = Decimal('0')
    students_graduated: int = 0  # Completed program
    avg_score_improvement: float = 0.0

    created_at: datetime = None


class PartnershipManager:
    """Manage all partnerships"""

    def __init__(self, db_connection=None):
        self.db = db_connection
        self.partners: List[Partner] = []
        self.government_partners: Dict[str, GovernmentPartner] = {}
        self.telco_partners: Dict[str, TelcoPartner] = {}
        self.device_partners: Dict[str, DevicePartner] = {}
        self.ngo_sponsors: Dict[str, NGOSponsor] = {}

    # Partner CRUD operations

    def add_partner(self, partner: Partner) -> str:
        """Add a new partner"""
        if not partner.partner_id:
            partner.partner_id = self._generate_partner_id()

        partner.created_at = datetime.now()
        partner.updated_at = datetime.now()

        self.partners.append(partner)

        return partner.partner_id

    def get_partner(self, partner_id: str) -> Optional[Partner]:
        """Get partner by ID"""
        for partner in self.partners:
            if partner.partner_id == partner_id:
                return partner
        return None

    def update_partner_status(
        self,
        partner_id: str,
        new_status: PartnershipStatus,
        notes: str = "",
    ) -> bool:
        """Update partnership status"""
        partner = self.get_partner(partner_id)
        if not partner:
            return False

        partner.status = new_status
        partner.updated_at = datetime.now()

        if notes:
            partner.notes = f"{partner.notes}\n[{datetime.now()}] Status: {new_status.value} - {notes}"

        # Set dates based on status
        if new_status == PartnershipStatus.CONTRACT_SIGNED:
            partner.partnership_start_date = datetime.now()
        elif new_status == PartnershipStatus.ACTIVE and not partner.partnership_start_date:
            partner.partnership_start_date = datetime.now()

        return True

    # Government partnerships

    def add_government_partner(
        self,
        partner: Partner,
        gov_details: GovernmentPartner,
    ) -> str:
        """Add government partnership"""
        partner_id = self.add_partner(partner)
        gov_details.partner_id = partner_id
        gov_details.created_at = datetime.now()
        self.government_partners[partner_id] = gov_details

        return partner_id

    def get_government_partnerships(self) -> List[Dict[str, Any]]:
        """Get all government partnerships"""
        result = []

        for partner in self.partners:
            if partner.type == PartnerType.GOVERNMENT:
                gov_details = self.government_partners.get(partner.partner_id)
                result.append({
                    "partner": partner,
                    "details": gov_details,
                })

        return result

    def calculate_government_revenue(self) -> Decimal:
        """Calculate total revenue from government partnerships"""
        total = Decimal('0')

        for gov_partner in self.government_partners.values():
            if gov_partner.contract_value_yearly:
                # Convert yearly to monthly
                total += gov_partner.contract_value_yearly / 12

        return total

    # Telco partnerships

    def add_telco_partner(
        self,
        partner: Partner,
        telco_details: TelcoPartner,
    ) -> str:
        """Add telco partnership"""
        partner_id = self.add_partner(partner)
        telco_details.partner_id = partner_id
        telco_details.created_at = datetime.now()
        self.telco_partners[partner_id] = telco_details

        return partner_id

    def get_active_data_bundles(self) -> List[Dict[str, Any]]:
        """Get all active education data bundles"""
        bundles = []

        for partner_id, telco in self.telco_partners.items():
            if telco.education_bundle_enabled:
                partner = self.get_partner(partner_id)
                if partner and partner.status == PartnershipStatus.ACTIVE:
                    bundles.append({
                        "telco": telco.telco_name,
                        "price": telco.bundle_price_ngn,
                        "size_gb": telco.bundle_size_gb,
                        "discount": telco.discount_percent,
                        "zero_rating": telco.zero_rating_enabled,
                    })

        return bundles

    # Device partnerships

    def add_device_partner(
        self,
        partner: Partner,
        device_details: DevicePartner,
    ) -> str:
        """Add device manufacturer partnership"""
        partner_id = self.add_partner(partner)
        device_details.partner_id = partner_id
        device_details.created_at = datetime.now()
        self.device_partners[partner_id] = device_details

        return partner_id

    def get_active_device_subsidies(self) -> List[Dict[str, Any]]:
        """Get all active device subsidy programs"""
        subsidies = []

        for partner_id, device in self.device_partners.items():
            if device.subsidy_program_active:
                partner = self.get_partner(partner_id)
                if partner and partner.status == PartnershipStatus.ACTIVE:
                    subsidies.append({
                        "manufacturer": device.manufacturer_name,
                        "subsidy_amount": device.subsidy_amount_ngn,
                        "models": device.device_models,
                        "bundled_subscription_months": device.subscription_duration_months,
                    })

        return subsidies

    # NGO sponsorships

    def add_ngo_sponsor(
        self,
        partner: Partner,
        ngo_details: NGOSponsor,
    ) -> str:
        """Add NGO/Corporate sponsor"""
        partner_id = self.add_partner(partner)
        ngo_details.partner_id = partner_id
        ngo_details.created_at = datetime.now()
        self.ngo_sponsors[partner_id] = ngo_details

        return partner_id

    def allocate_sponsored_students(
        self,
        sponsor_id: str,
        num_students: int,
        schools: List[str],
    ) -> bool:
        """Allocate sponsored student slots to schools"""
        ngo = self.ngo_sponsors.get(sponsor_id)
        if not ngo:
            return False

        # Check if sponsor has capacity
        available = ngo.students_sponsored - self._get_allocated_students(sponsor_id)
        if available < num_students:
            return False

        # Allocate students
        # Implementation would update database to assign sponsor to students

        return True

    def _get_allocated_students(self, sponsor_id: str) -> int:
        """Get number of already allocated sponsored students"""
        # Implementation would query database
        return 0

    def get_sponsorship_impact_report(self, sponsor_id: str) -> Dict[str, Any]:
        """Generate impact report for sponsor"""
        ngo = self.ngo_sponsors.get(sponsor_id)
        if not ngo:
            return {}

        # Get sponsored students data
        # This would query actual student performance data

        return {
            "sponsor": ngo.organization_name,
            "students_sponsored": ngo.students_sponsored,
            "monthly_investment": ngo.total_monthly_commitment,
            "total_invested": ngo.total_invested,
            "students_active": ngo.students_sponsored,  # Would query actual
            "students_graduated": ngo.students_graduated,
            "avg_score_improvement": ngo.avg_score_improvement,
            "avg_weekly_active_rate": 75.0,  # Would calculate from data
            "top_performing_students": [],  # Would fetch from database
            "testimonials": [],  # Would fetch from database
            "impact_summary": f"{ngo.students_sponsored} students from underserved communities gained access to quality education technology",
        }

    # Reporting and analytics

    def get_partnership_dashboard(self) -> Dict[str, Any]:
        """Comprehensive partnership dashboard"""
        active_partners = [p for p in self.partners if p.status == PartnershipStatus.ACTIVE]

        return {
            "summary": {
                "total_partners": len(self.partners),
                "active_partners": len(active_partners),
                "government": len([p for p in active_partners if p.type == PartnerType.GOVERNMENT]),
                "telcos": len([p for p in active_partners if p.type == PartnerType.TELCO]),
                "device_manufacturers": len([p for p in active_partners if p.type == PartnerType.DEVICE_MANUFACTURER]),
                "ngo_sponsors": len([p for p in active_partners if p.type == PartnerType.NGO]),
            },

            "impact": {
                "total_students_impacted": sum(p.students_impacted for p in active_partners),
                "total_schools_impacted": sum(p.schools_impacted for p in active_partners),
                "sponsored_students": sum(ngo.students_sponsored for ngo in self.ngo_sponsors.values()),
            },

            "financial": {
                "total_contract_value": sum(p.contract_value for p in active_partners),
                "government_revenue_monthly": self.calculate_government_revenue(),
                "sponsorship_revenue_monthly": sum(ngo.total_monthly_commitment for ngo in self.ngo_sponsors.values()),
            },

            "data_bundles": len(self.get_active_data_bundles()),
            "device_subsidies": len(self.get_active_device_subsidies()),
        }

    def get_partnership_pipeline(self) -> Dict[PartnershipStatus, int]:
        """Get partnership pipeline by status"""
        pipeline = {}

        for status in PartnershipStatus:
            count = len([p for p in self.partners if p.status == status])
            pipeline[status] = count

        return pipeline

    def get_partners_by_type(self, partner_type: PartnerType) -> List[Partner]:
        """Get all partners of a specific type"""
        return [p for p in self.partners if p.type == partner_type]

    # Helper methods

    def _generate_partner_id(self) -> str:
        """Generate unique partner ID"""
        import uuid
        return f"PARTNER_{uuid.uuid4().hex[:12]}"


# Example usage
if __name__ == "__main__":
    manager = PartnershipManager()

    # Example 1: Add Lagos State Government partnership
    lagos_state = Partner(
        partner_id="",
        name="Lagos State Ministry of Education",
        type=PartnerType.GOVERNMENT,
        status=PartnershipStatus.IN_DISCUSSION,
        contact_name="Commissioner of Education",
        contact_email="commissioner@lagosstate.gov.ng",
        contact_phone="+234 XXX XXX XXXX",
        contract_value=Decimal('24000000'),  # ₦24M/year
    )

    lagos_details = GovernmentPartner(
        partner_id="",
        ministry_name="Lagos State Ministry of Education",
        level="state",
        state="Lagos",
        contract_type="state_wide",
        num_schools=50,
        num_students=10000,
        contract_value_yearly=Decimal('24000000'),
        free_tier_provided=False,  # Paying for Premium features
        training_included=True,
        dedicated_support=True,
        sla_uptime="99.9%",
        quarterly_reports_required=True,
        payment_schedule="annual",
        billing_entity="Lagos State Universal Basic Education Board",
    )

    partner_id = manager.add_government_partner(lagos_state, lagos_details)
    print(f"Added Lagos State partnership: {partner_id}")

    # Example 2: Add MTN telco partnership
    mtn_partner = Partner(
        partner_id="",
        name="MTN Nigeria",
        type=PartnerType.TELCO,
        status=PartnershipStatus.CONTRACT_SIGNED,
        contact_name="Head of Education Partnerships",
        contact_email="education@mtn.ng",
        contact_phone="+234 XXX XXX XXXX",
        website="https://www.mtn.ng",
    )

    mtn_details = TelcoPartner(
        partner_id="",
        telco_name="MTN",
        education_bundle_enabled=True,
        bundle_price_ngn=Decimal('200'),
        bundle_size_gb=1,
        discount_percent=50,
        zero_rating_enabled=True,
        zero_rated_domains=["*.examstutor.ng", "cdn.examstutor.ng"],
        co_marketing_agreement=True,
        marketing_budget_ngn=Decimal('5000000'),
        revenue_share_enabled=True,
        revenue_share_percent=10,
    )

    mtn_id = manager.add_telco_partner(mtn_partner, mtn_details)
    print(f"Added MTN partnership: {mtn_id}")
    manager.update_partner_status(mtn_id, PartnershipStatus.ACTIVE, "Partnership launched")

    # Example 3: Add Tecno device partnership
    tecno_partner = Partner(
        partner_id="",
        name="Tecno Mobile Nigeria",
        type=PartnerType.DEVICE_MANUFACTURER,
        status=PartnershipStatus.NEGOTIATING,
        contact_name="Head of Partnerships",
        contact_email="partnerships@tecno.ng",
        contact_phone="+234 XXX XXX XXXX",
    )

    tecno_details = DevicePartner(
        partner_id="",
        manufacturer_name="Tecno",
        app_preinstalled=True,
        device_models=["Spark 10 Pro", "Camon 20", "Phantom X2"],
        subsidy_program_active=True,
        subsidy_amount_ngn=Decimal('5000'),
        bundled_subscription=True,
        subscription_duration_months=12,
        co_branded_devices=True,
        education_device_line=True,
        revenue_share_percent=15,
    )

    tecno_id = manager.add_device_partner(tecno_partner, tecno_details)
    print(f"Added Tecno partnership: {tecno_id}")

    # Example 4: Add NGO sponsor
    etf_sponsor = Partner(
        partner_id="",
        name="Education Trust Fund",
        type=PartnerType.NGO,
        status=PartnershipStatus.ACTIVE,
        contact_name="Executive Director",
        contact_email="director@etf.org.ng",
        contact_phone="+234 XXX XXX XXXX",
    )

    etf_details = NGOSponsor(
        partner_id="",
        organization_name="Education Trust Fund",
        organization_type="ngo",
        students_sponsored=500,
        sponsorship_per_student_monthly=Decimal('300'),
        total_monthly_commitment=Decimal('150000'),
        target_demographics="rural underprivileged students",
        target_regions=["Ondo", "Oyo", "Kano"],
        impact_reports_frequency="monthly",
        student_testimonials_required=True,
        branding_on_platform=True,
        certificates_for_students=True,
        tax_deduction_documentation=True,
        public_recognition=True,
    )

    etf_id = manager.add_ngo_sponsor(etf_sponsor, etf_details)
    print(f"Added ETF sponsorship: {etf_id}")

    # Get partnership dashboard
    dashboard = manager.get_partnership_dashboard()
    print("\nPartnership Dashboard:")
    print(f"  Active partners: {dashboard['summary']['active_partners']}")
    print(f"  Students impacted: {dashboard['impact']['total_students_impacted']}")
    print(f"  Sponsored students: {dashboard['impact']['sponsored_students']}")
    print(f"  Government revenue/month: ₦{dashboard['financial']['government_revenue_monthly']:,.2f}")
    print(f"  Active data bundles: {dashboard['data_bundles']}")
    print(f"  Active device subsidies: {dashboard['device_subsidies']}")

    # Get active data bundles
    bundles = manager.get_active_data_bundles()
    print("\nActive Data Bundles:")
    for bundle in bundles:
        print(f"  {bundle['telco']}: {bundle['size_gb']}GB for ₦{bundle['price']} ({bundle['discount']}% discount)")
