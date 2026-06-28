import pytest
from src.services.ai_generator import (
    AIGenerator,
    CAT_RESTAURANT, CAT_SALON, CAT_CLINIC, CAT_HOSPITAL,
    CAT_GYM, CAT_REALESTATE, CAT_EDUCATION, CAT_ECOMMERCE,
    CAT_HOTEL, CAT_TRAVEL, CAT_PHARMACY, CAT_SUPERMARKET, CAT_SERVICE,
    ORDERING_CATEGORIES, BOOKING_CATEGORIES, DELIVERY_FEEDBACK_CATEGORIES,
)
from src.engine.quality_validator import WorkflowQualityValidator


# ---------------------------------------------------------------------------
# Section 1 — detect_category: capability_packs input (Fix 1)
# ---------------------------------------------------------------------------

class TestDetectCategoryFromPacks:

    def test_restaurant_pack_lowercase(self):
        cat = AIGenerator.detect_category("", ["restaurant"])
        assert cat == "restaurant", f"Expected 'restaurant', got '{cat}'"

    def test_restaurant_pack_mixed_case(self):
        """Pack names from the frontend may arrive in any casing."""
        cat = AIGenerator.detect_category("", ["Restaurant"])
        assert cat == "restaurant"

    def test_restaurant_pack_upper(self):
        cat = AIGenerator.detect_category("", ["RESTAURANT"])
        assert cat == "restaurant"

    def test_salon_pack(self):
        cat = AIGenerator.detect_category("", ["salon"])
        assert cat == "salon"

    def test_hospital_pack(self):
        cat = AIGenerator.detect_category("", ["hospital"])
        assert cat == "hospital"

    def test_clinic_pack(self):
        cat = AIGenerator.detect_category("", ["clinic"])
        assert cat == "clinic"

    def test_gym_pack(self):
        cat = AIGenerator.detect_category("", ["gym"])
        assert cat == "gym"

    def test_ecommerce_pack(self):
        cat = AIGenerator.detect_category("", ["ecommerce"])
        assert cat == "ecommerce"

    def test_supermarket_pack(self):
        cat = AIGenerator.detect_category("", ["supermarket"])
        assert cat == "supermarket"

    def test_realestate_pack_alias(self):
        """'real estate' with space should normalise to 'realestate'."""
        cat = AIGenerator.detect_category("", ["real estate"])
        assert cat == "realestate"

    def test_realestate_pack_underscore_alias(self):
        cat = AIGenerator.detect_category("", ["real_estate"])
        assert cat == "realestate"

    def test_education_pack(self):
        cat = AIGenerator.detect_category("", ["education"])
        assert cat == "education"

    def test_service_business_pack_alias(self):
        cat = AIGenerator.detect_category("", ["service_business"])
        assert cat == "servicebusiness"

    def test_pharmacy_pack(self):
        cat = AIGenerator.detect_category("", ["pharmacy"])
        assert cat == "pharmacy"

    def test_first_pack_wins(self):
        """When multiple packs supplied, first one wins."""
        cat = AIGenerator.detect_category("", ["restaurant", "salon"])
        assert cat == "restaurant"


# ---------------------------------------------------------------------------
# Section 2 — detect_category: keyword fallback
# ---------------------------------------------------------------------------

class TestDetectCategoryKeywords:

    def test_pizza_keyword(self):
        cat = AIGenerator.detect_category("We sell pizza and burgers", [])
        assert cat == "restaurant"

    def test_food_keyword(self):
        cat = AIGenerator.detect_category("Best food delivery in the city", [])
        assert cat == "restaurant"

    def test_cafe_keyword(self):
        cat = AIGenerator.detect_category("A cosy cafe in downtown", [])
        assert cat == "restaurant"

    def test_supermarket_keyword(self):
        cat = AIGenerator.detect_category("Online grocery and supermarket delivery", [])
        assert cat == "supermarket"

    def test_grocery_keyword(self):
        cat = AIGenerator.detect_category("Fresh groceries delivered to your door", [])
        assert cat == "supermarket"

    def test_hair_keyword(self):
        cat = AIGenerator.detect_category("Hair styling and nail art studio", [])
        assert cat == "salon"

    def test_barber_keyword(self):
        cat = AIGenerator.detect_category("Premium barber shop", [])
        assert cat == "salon"

    def test_doctor_keyword(self):
        cat = AIGenerator.detect_category("Book a doctor consultation", [])
        assert cat == "clinic"

    def test_hospital_keyword(self):
        cat = AIGenerator.detect_category("Multispecialty hospital admissions", [])
        assert cat == "hospital"

    def test_gym_keyword(self):
        cat = AIGenerator.detect_category("Gym membership and personal trainer sessions", [])
        assert cat == "gym"

    def test_ecommerce_keyword(self):
        cat = AIGenerator.detect_category("Our online store ships products worldwide", [])
        assert cat == "ecommerce"

    def test_pharmacy_keyword(self):
        cat = AIGenerator.detect_category("Order prescription medicine online", [])
        assert cat == "pharmacy"

    def test_education_keyword_course(self):
        cat = AIGenerator.detect_category("Enroll in our online courses", [])
        assert cat == "education"

    def test_education_keyword_university(self):
        cat = AIGenerator.detect_category("University admission and enrollment platform", [])
        assert cat == "education"

    def test_education_keyword_coaching(self):
        cat = AIGenerator.detect_category("1-on-1 coaching and tutoring sessions", [])
        assert cat == "education"

    def test_unknown_description_defaults_to_service(self):
        cat = AIGenerator.detect_category("We do miscellaneous consulting", [])
        assert cat == "servicebusiness"

    def test_capability_packs_take_priority_over_keywords(self):
        """Even if description says 'restaurant', packs override."""
        cat = AIGenerator.detect_category(
            "We serve great pizza and burgers",
            ["salon"]
        )
        assert cat == "salon"


# ---------------------------------------------------------------------------
# Section 3 — build_programmatic_portfolio: correct workflow selected (Fix 2)
# ---------------------------------------------------------------------------

class TestBuildProgrammaticPortfolio:

    # --- Restaurant → Ordering Workflow ---
    def test_restaurant_generates_ordering_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_001", "Pizza Planet", "restaurant", []
        )
        assert "Ordering Workflow" in portfolio, (
            f"Expected 'Ordering Workflow' in portfolio keys, got: {list(portfolio.keys())}"
        )
        assert "General Service" not in portfolio
        assert "Booking Workflow" not in portfolio

    def test_ecommerce_generates_ordering_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_002", "ShopZone", "ecommerce", []
        )
        assert "Ordering Workflow" in portfolio

    def test_pharmacy_generates_ordering_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_003", "MediPlus", "pharmacy", []
        )
        assert "Ordering Workflow" in portfolio

    def test_supermarket_generates_ordering_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_009", "FreshMart", "supermarket", []
        )
        assert "Ordering Workflow" in portfolio
        assert "General Service" not in portfolio
        assert "Booking Workflow" not in portfolio

    # --- Salon → Booking Workflow ---
    def test_salon_generates_booking_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_004", "Luxe Salon", "salon", []
        )
        assert "Booking Workflow" in portfolio, (
            f"Expected 'Booking Workflow', got: {list(portfolio.keys())}"
        )
        assert "Ordering Workflow" not in portfolio
        assert "General Service" not in portfolio

    # --- Hospital → Booking Workflow ---
    def test_hospital_generates_booking_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_005", "Apollo Hospital", "hospital", []
        )
        assert "Booking Workflow" in portfolio

    # --- Clinic → Booking Workflow ---
    def test_clinic_generates_booking_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_006", "City Clinic", "clinic", []
        )
        assert "Booking Workflow" in portfolio

    # --- Gym → Booking Workflow ---
    def test_gym_generates_booking_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_007", "TitanFit", "gym", []
        )
        assert "Booking Workflow" in portfolio

    # --- Education → Booking Workflow (Part 1 fix) ---
    def test_education_generates_booking_workflow(self):
        """REGRESSION guard: Education must NOT fall into General Service."""
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_010", "EduLearn Academy", "education", []
        )
        assert "Booking Workflow" in portfolio, (
            f"FAIL: Education fell through to: {list(portfolio.keys())}. "
            f"Ensure CAT_EDUCATION is in BOOKING_CATEGORIES."
        )
        assert "General Service" not in portfolio
        assert "Ordering Workflow" not in portfolio

    def test_education_portfolio_has_all_three_workflows(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_010", "EduLearn Academy", "education", []
        )
        assert "Booking Workflow" in portfolio
        assert "Support Workflow" in portfolio
        assert "Feedback Workflow" in portfolio

    # --- Unknown → General Service ---
    def test_unknown_category_generates_general_service(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_008", "Random Biz", "unknowncategory", []
        )
        assert "General Service" in portfolio
        assert "Ordering Workflow" not in portfolio
        assert "Booking Workflow" not in portfolio

    # --- Every portfolio must include Support and Feedback ---
    def test_restaurant_portfolio_has_support_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_001", "Pizza Planet", "restaurant", []
        )
        assert "Support Workflow" in portfolio

    def test_restaurant_portfolio_has_feedback_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_001", "Pizza Planet", "restaurant", []
        )
        assert "Feedback Workflow" in portfolio

    def test_salon_portfolio_has_support_and_feedback(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_004", "Luxe Salon", "salon", []
        )
        assert "Support Workflow" in portfolio
        assert "Feedback Workflow" in portfolio


# ---------------------------------------------------------------------------
# Section 4 — Feedback trigger event (Fix 2 + Spec Section M)
# ---------------------------------------------------------------------------

class TestFeedbackWorkflowTrigger:

    def test_restaurant_feedback_triggers_on_delivery_completed(self):
        wf = AIGenerator.get_feedback_workflow("biz_001", "Pizza Planet", "restaurant")
        assert wf["trigger_event"] == "DELIVERY_COMPLETED", (
            f"Restaurant feedback must trigger on DELIVERY_COMPLETED, got '{wf['trigger_event']}'"
        )

    def test_ecommerce_feedback_triggers_on_delivery_completed(self):
        wf = AIGenerator.get_feedback_workflow("biz_002", "ShopZone", "ecommerce")
        assert wf["trigger_event"] == "DELIVERY_COMPLETED"

    def test_supermarket_feedback_triggers_on_delivery_completed(self):
        wf = AIGenerator.get_feedback_workflow("biz_009", "FreshMart", "supermarket")
        assert wf["trigger_event"] == "DELIVERY_COMPLETED"

    def test_salon_feedback_triggers_on_booking_confirmed(self):
        wf = AIGenerator.get_feedback_workflow("biz_004", "Luxe Salon", "salon")
        assert wf["trigger_event"] == "BOOKING_CONFIRMED", (
            f"Salon feedback must trigger on BOOKING_CONFIRMED, got '{wf['trigger_event']}'"
        )

    def test_hospital_feedback_triggers_on_booking_confirmed(self):
        wf = AIGenerator.get_feedback_workflow("biz_005", "Apollo Hospital", "hospital")
        assert wf["trigger_event"] == "BOOKING_CONFIRMED"

    def test_clinic_feedback_triggers_on_booking_confirmed(self):
        wf = AIGenerator.get_feedback_workflow("biz_006", "City Clinic", "clinic")
        assert wf["trigger_event"] == "BOOKING_CONFIRMED"

    def test_gym_feedback_triggers_on_booking_confirmed(self):
        wf = AIGenerator.get_feedback_workflow("biz_007", "TitanFit", "gym")
        assert wf["trigger_event"] == "BOOKING_CONFIRMED"

    def test_education_feedback_triggers_on_booking_confirmed(self):
        wf = AIGenerator.get_feedback_workflow("biz_010", "EduLearn Academy", "education")
        assert wf["trigger_event"] == "BOOKING_CONFIRMED", (
            f"Education feedback must trigger on BOOKING_CONFIRMED, got '{wf['trigger_event']}'"
        )

    def test_pharmacy_feedback_triggers_on_delivery_completed(self):
        wf = AIGenerator.get_feedback_workflow("biz_003", "MediPlus", "pharmacy")
        assert wf["trigger_event"] == "DELIVERY_COMPLETED"


# ---------------------------------------------------------------------------
# Section 5 — Ordering Workflow structure
# ---------------------------------------------------------------------------

class TestOrderingWorkflowContent:

    def test_restaurant_ordering_has_full_delivery_chain(self):
        wf = AIGenerator.get_ordering_workflow("biz_001", "Pizza Planet", "restaurant", [])
        modules = [n["module_name"] for n in wf["nodes"].values()]
        assert "show_menu"       in modules
        assert "collect_cart"    in modules
        assert "calculate_total" in modules
        assert "create_order"    in modules
        assert "create_payment"  in modules
        assert "confirm_payment" in modules
        assert "collect_address" in modules
        assert "create_delivery" in modules
        assert "notify_customer" in modules

    def test_restaurant_menu_has_no_haircut_content(self):
        """The single most important regression check — no salon content in restaurant flow."""
        wf = AIGenerator.get_ordering_workflow("biz_001", "Pizza Planet", "restaurant", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"].lower()
        assert "haircut"   not in menu_text, "REGRESSION: salon content in restaurant ordering workflow"
        assert "hair wash" not in menu_text, "REGRESSION: salon content in restaurant ordering workflow"
        assert "styling"   not in menu_text, "REGRESSION: salon content in restaurant ordering workflow"

    def test_pharmacy_ordering_has_medicine_defaults(self):
        wf = AIGenerator.get_ordering_workflow("biz_003", "MediPlus", "pharmacy", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert "Cough Syrup" in menu_text or "Pain Reliever" in menu_text

    def test_supermarket_ordering_has_grocery_defaults(self):
        wf = AIGenerator.get_ordering_workflow("biz_009", "FreshMart", "supermarket", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert any(w in menu_text for w in ["Vegetable", "Bread", "Milk", "Eggs"]), (
            f"Supermarket menu must contain grocery items. Got: {menu_text[:200]}"
        )

    def test_restaurant_ordering_fsm_table_complete(self):
        wf = AIGenerator.get_ordering_workflow("biz_001", "Pizza Planet", "restaurant", [])
        table = wf["fsm_transition_table"]
        assert "START"    in table
        assert "MENU"     in table
        assert "CART"     in table
        assert "CHECKOUT" in table
        assert "PAYMENT"  in table


# ---------------------------------------------------------------------------
# Section 6 — Booking Workflow: correct defaults per sub-category
# ---------------------------------------------------------------------------

class TestBookingWorkflowDefaults:

    def test_salon_has_haircut_content(self):
        wf = AIGenerator.get_booking_workflow("biz_004", "Luxe Salon", "salon", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert "Haircut" in menu_text

    def test_clinic_has_consultation_content(self):
        wf = AIGenerator.get_booking_workflow("biz_006", "City Clinic", "clinic", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert "Consultation" in menu_text or "consultation" in menu_text.lower()

    def test_hospital_has_consultation_content(self):
        wf = AIGenerator.get_booking_workflow("biz_005", "Apollo Hospital", "hospital", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert "Consultation" in menu_text or "consultation" in menu_text.lower()

    def test_gym_has_membership_content(self):
        wf = AIGenerator.get_booking_workflow("biz_007", "TitanFit", "gym", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert "Membership" in menu_text or "membership" in menu_text.lower()

    def test_education_has_course_content(self):
        """Task 1.3: Education booking must contain course-specific content."""
        wf = AIGenerator.get_booking_workflow("biz_010", "EduLearn Academy", "education", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert any(w in menu_text.lower() for w in ["course", "program", "coaching"]), (
            f"Education booking workflow must contain course content. Got: {menu_text[:200]}"
        )

    def test_education_booking_has_required_modules(self):
        """Task 1.3: Education booking must contain all required modules."""
        wf = AIGenerator.get_booking_workflow("biz_010", "EduLearn Academy", "education", [])
        modules = [n["module_name"] for n in wf["nodes"].values()]
        for required in ["show_menu", "collect_cart", "create_order",
                         "create_payment", "confirm_payment", "notify_customer"]:
            assert required in modules, f"Education booking missing module: {required}"

    def test_realestate_has_property_tour_content(self):
        wf = AIGenerator.get_booking_workflow("biz_011", "PropertyHub", "realestate", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert any(w in menu_text.lower() for w in ["property", "apartment", "tour"])

    def test_travel_has_trip_content(self):
        wf = AIGenerator.get_booking_workflow("biz_012", "WanderTrips", "travel", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert any(w in menu_text.lower() for w in ["tour", "package", "trip"])


# ---------------------------------------------------------------------------
# Section 7 — Category constant sets are internally consistent
# ---------------------------------------------------------------------------

class TestCategoryConstants:

    def test_ordering_categories_are_correct(self):
        assert CAT_RESTAURANT  in ORDERING_CATEGORIES
        assert CAT_ECOMMERCE   in ORDERING_CATEGORIES
        assert CAT_PHARMACY    in ORDERING_CATEGORIES
        assert CAT_SUPERMARKET in ORDERING_CATEGORIES

    def test_booking_categories_are_correct(self):
        assert CAT_SALON      in BOOKING_CATEGORIES
        assert CAT_CLINIC     in BOOKING_CATEGORIES
        assert CAT_HOSPITAL   in BOOKING_CATEGORIES
        assert CAT_GYM        in BOOKING_CATEGORIES
        assert CAT_HOTEL      in BOOKING_CATEGORIES
        assert CAT_TRAVEL     in BOOKING_CATEGORIES
        assert CAT_REALESTATE in BOOKING_CATEGORIES
        assert CAT_EDUCATION  in BOOKING_CATEGORIES   # Fix 1 regression guard

    def test_education_not_in_general_service_path(self):
        """Education must be in BOOKING_CATEGORIES so it never reaches get_general_service_workflow."""
        assert CAT_EDUCATION in BOOKING_CATEGORIES
        assert CAT_EDUCATION not in ORDERING_CATEGORIES

    def test_no_overlap_between_ordering_and_booking(self):
        overlap = ORDERING_CATEGORIES & BOOKING_CATEGORIES
        assert not overlap, f"Categories appear in both sets: {overlap}"

    def test_delivery_feedback_is_subset_of_ordering(self):
        assert DELIVERY_FEEDBACK_CATEGORIES.issubset(ORDERING_CATEGORIES)

    def test_supermarket_in_delivery_feedback(self):
        assert CAT_SUPERMARKET in DELIVERY_FEEDBACK_CATEGORIES

    def test_salon_not_in_delivery_feedback(self):
        assert CAT_SALON not in DELIVERY_FEEDBACK_CATEGORIES

    def test_hospital_not_in_delivery_feedback(self):
        assert CAT_HOSPITAL not in DELIVERY_FEEDBACK_CATEGORIES

    def test_education_not_in_delivery_feedback(self):
        assert CAT_EDUCATION not in DELIVERY_FEEDBACK_CATEGORIES


# ---------------------------------------------------------------------------
# Section 8 — WorkflowQualityValidator (Part 3)
# ---------------------------------------------------------------------------

def _restaurant_graph():
    """Builds the standard restaurant programmatic ordering workflow graph."""
    return AIGenerator.get_ordering_workflow("biz_001", "Pizza Planet", "restaurant", [])


def _education_graph():
    return AIGenerator.get_booking_workflow("biz_010", "EduLearn Academy", "education", [])


def _hospital_graph():
    return AIGenerator.get_booking_workflow("biz_005", "Apollo Hospital", "hospital", [])


def _realestate_graph():
    return AIGenerator.get_booking_workflow("biz_011", "PropertyHub", "realestate", [])


class TestWorkflowQualityValidator:

    def test_restaurant_valid_workflow_passes(self):
        graph = _restaurant_graph()
        report = WorkflowQualityValidator.validate(graph, "restaurant")
        assert report["passed"], (
            f"Restaurant programmatic workflow failed quality validation:\n"
            + "\n".join(f"  [{v['severity']}] {v['rule']}: {v['hint']}" for v in report["violations"])
        )

    def test_restaurant_module_order_is_correct(self):
        graph = _restaurant_graph()
        report = WorkflowQualityValidator.validate(graph, "restaurant")
        order = report["module_order"]
        # show_menu must come before collect_cart
        assert order.index("show_menu") < order.index("collect_cart")
        # create_order must come before create_payment
        assert order.index("create_order") < order.index("create_payment")
        # collect_address must come before create_delivery
        assert order.index("collect_address") < order.index("create_delivery")

    def test_education_valid_workflow_passes(self):
        graph = _education_graph()
        report = WorkflowQualityValidator.validate(graph, "education")
        assert report["passed"], (
            f"Education programmatic workflow failed quality validation:\n"
            + "\n".join(f"  [{v['severity']}] {v['rule']}: {v['hint']}" for v in report["violations"])
        )

    def test_hospital_valid_workflow_passes(self):
        graph = _hospital_graph()
        report = WorkflowQualityValidator.validate(graph, "hospital")
        assert report["passed"], (
            f"Hospital programmatic workflow failed quality validation:\n"
            + "\n".join(f"  [{v['severity']}] {v['rule']}: {v['hint']}" for v in report["violations"])
        )

    def test_realestate_valid_workflow_passes(self):
        graph = _realestate_graph()
        report = WorkflowQualityValidator.validate(graph, "realestate")
        assert report["passed"], (
            f"RealEstate programmatic workflow failed quality validation:\n"
            + "\n".join(f"  [{v['severity']}] {v['rule']}: {v['hint']}" for v in report["violations"])
        )

    def test_delivery_before_payment_fails_restaurant_validation(self):
        """Inverted ordering must be detected as an error."""
        graph = _restaurant_graph()
        # Manually break ordering: swap create_payment and create_delivery positions
        # by redirecting edges so delivery comes first
        # Simplest: inject a fake graph with wrong order
        bad_graph = {
            "nodes": {
                "node_menu":     {"id": "node_menu",     "module_name": "show_menu",       "fsm_transition_to": "MENU",      "config": {}},
                "node_collect":  {"id": "node_collect",  "module_name": "collect_cart",    "fsm_transition_to": "CART",      "config": {}},
                "node_total":    {"id": "node_total",    "module_name": "calculate_total", "fsm_transition_to": "CHECKOUT",  "config": {}},
                "node_order":    {"id": "node_order",    "module_name": "create_order",    "fsm_transition_to": "CHECKOUT",  "config": {}},
                # WRONG: delivery before payment
                "node_delivery": {"id": "node_delivery", "module_name": "create_delivery", "fsm_transition_to": "CONFIRMED", "config": {}},
                "node_payment":  {"id": "node_payment",  "module_name": "create_payment",  "fsm_transition_to": "PAYMENT",   "config": {}},
                "node_confirm":  {"id": "node_confirm",  "module_name": "confirm_payment", "fsm_transition_to": "CONFIRMED", "config": {}},
                "node_address":  {"id": "node_address",  "module_name": "collect_address", "fsm_transition_to": "CONFIRMED", "config": {}},
                "node_notify":   {"id": "node_notify",   "module_name": "notify_customer", "fsm_transition_to": "CONFIRMED", "config": {}},
            },
            "edges": [
                {"from_node": "node_menu",     "to_node": "node_collect",  "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_collect",  "to_node": "node_total",    "condition": {"type": "always",    "value": ""}},
                {"from_node": "node_total",    "to_node": "node_order",    "condition": {"type": "always",    "value": ""}},
                {"from_node": "node_order",    "to_node": "node_delivery", "condition": {"type": "always",    "value": ""}},  # WRONG
                {"from_node": "node_delivery", "to_node": "node_payment",  "condition": {"type": "always",    "value": ""}},
                {"from_node": "node_payment",  "to_node": "node_confirm",  "condition": {"type": "always",    "value": ""}},
                {"from_node": "node_confirm",  "to_node": "node_address",  "condition": {"type": "always",    "value": ""}},
                {"from_node": "node_address",  "to_node": "node_notify",   "condition": {"type": "always",    "value": ""}},
            ],
            "fsm_transition_table": {}
        }
        report = WorkflowQualityValidator.validate(bad_graph, "restaurant")
        assert not report["passed"], "Delivery-before-payment ordering must fail quality validation"
        error_rules = [v["rule"] for v in report["violations"] if v["severity"] == "error"]
        assert any("ordering_error" in r for r in error_rules), (
            f"Expected an ordering_error violation, got: {error_rules}"
        )

    def test_unknown_category_does_not_crash_validator(self):
        graph = AIGenerator.get_general_service_workflow("biz_000", "Unknown Biz", "unknowncategory")
        report = WorkflowQualityValidator.validate(graph, "unknowncategory")
        assert "passed" in report
        assert "violations" in report
        assert "module_order" in report



# ---------------------------------------------------------------------------
# Section 1 — detect_category: capability_packs input (Fix 1)
# ---------------------------------------------------------------------------

class TestDetectCategoryFromPacks:

    def test_restaurant_pack_lowercase(self):
        cat = AIGenerator.detect_category("", ["restaurant"])
        assert cat == "restaurant", f"Expected 'restaurant', got '{cat}'"

    def test_restaurant_pack_mixed_case(self):
        """Pack names from the frontend may arrive in any casing."""
        cat = AIGenerator.detect_category("", ["Restaurant"])
        assert cat == "restaurant"

    def test_restaurant_pack_upper(self):
        cat = AIGenerator.detect_category("", ["RESTAURANT"])
        assert cat == "restaurant"

    def test_salon_pack(self):
        cat = AIGenerator.detect_category("", ["salon"])
        assert cat == "salon"

    def test_hospital_pack(self):
        cat = AIGenerator.detect_category("", ["hospital"])
        assert cat == "hospital"

    def test_clinic_pack(self):
        cat = AIGenerator.detect_category("", ["clinic"])
        assert cat == "clinic"

    def test_gym_pack(self):
        cat = AIGenerator.detect_category("", ["gym"])
        assert cat == "gym"

    def test_ecommerce_pack(self):
        cat = AIGenerator.detect_category("", ["ecommerce"])
        assert cat == "ecommerce"

    def test_realestate_pack_alias(self):
        """'real estate' with space should normalise to 'realestate'."""
        cat = AIGenerator.detect_category("", ["real estate"])
        assert cat == "realestate"

    def test_realestate_pack_underscore_alias(self):
        cat = AIGenerator.detect_category("", ["real_estate"])
        assert cat == "realestate"

    def test_education_pack(self):
        cat = AIGenerator.detect_category("", ["education"])
        assert cat == "education"

    def test_service_business_pack_alias(self):
        cat = AIGenerator.detect_category("", ["service_business"])
        assert cat == "servicebusiness"

    def test_first_pack_wins(self):
        """When multiple packs supplied, first one wins."""
        cat = AIGenerator.detect_category("", ["restaurant", "salon"])
        assert cat == "restaurant"


# ---------------------------------------------------------------------------
# Section 2 — detect_category: keyword fallback
# ---------------------------------------------------------------------------

class TestDetectCategoryKeywords:

    def test_pizza_keyword(self):
        cat = AIGenerator.detect_category("We sell pizza and burgers", [])
        assert cat == "restaurant"

    def test_food_keyword(self):
        cat = AIGenerator.detect_category("Best food delivery in the city", [])
        assert cat == "restaurant"

    def test_cafe_keyword(self):
        cat = AIGenerator.detect_category("A cosy cafe in downtown", [])
        assert cat == "restaurant"

    def test_hair_keyword(self):
        cat = AIGenerator.detect_category("Hair styling and nail art studio", [])
        assert cat == "salon"

    def test_barber_keyword(self):
        cat = AIGenerator.detect_category("Premium barber shop", [])
        assert cat == "salon"

    def test_doctor_keyword(self):
        cat = AIGenerator.detect_category("Book a doctor consultation", [])
        assert cat == "clinic"

    def test_hospital_keyword(self):
        cat = AIGenerator.detect_category("Multispecialty hospital admissions", [])
        assert cat == "hospital"

    def test_gym_keyword(self):
        cat = AIGenerator.detect_category("Gym membership and personal trainer sessions", [])
        assert cat == "gym"

    def test_ecommerce_keyword(self):
        cat = AIGenerator.detect_category("Our online store ships products worldwide", [])
        assert cat == "ecommerce"

    def test_pharmacy_keyword(self):
        cat = AIGenerator.detect_category("Order prescription medicine online", [])
        assert cat == "pharmacy"

    def test_unknown_description_defaults_to_service(self):
        cat = AIGenerator.detect_category("We do miscellaneous consulting", [])
        assert cat == "servicebusiness"

    def test_capability_packs_take_priority_over_keywords(self):
        """Even if description says 'restaurant', packs override."""
        cat = AIGenerator.detect_category(
            "We serve great pizza and burgers",
            ["salon"]
        )
        assert cat == "salon"


# ---------------------------------------------------------------------------
# Section 3 — build_programmatic_portfolio: correct workflow selected (Fix 2)
# ---------------------------------------------------------------------------

class TestBuildProgrammaticPortfolio:

    # --- Restaurant → Ordering Workflow ---
    def test_restaurant_generates_ordering_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_001", "Pizza Planet", "restaurant", []
        )
        assert "Ordering Workflow" in portfolio, (
            f"Expected 'Ordering Workflow' in portfolio keys, got: {list(portfolio.keys())}"
        )
        assert "General Service" not in portfolio
        assert "Booking Workflow" not in portfolio

    def test_ecommerce_generates_ordering_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_002", "ShopZone", "ecommerce", []
        )
        assert "Ordering Workflow" in portfolio

    def test_pharmacy_generates_ordering_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_003", "MediPlus", "pharmacy", []
        )
        assert "Ordering Workflow" in portfolio

    # --- Salon → Booking Workflow ---
    def test_salon_generates_booking_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_004", "Luxe Salon", "salon", []
        )
        assert "Booking Workflow" in portfolio, (
            f"Expected 'Booking Workflow', got: {list(portfolio.keys())}"
        )
        assert "Ordering Workflow" not in portfolio
        assert "General Service" not in portfolio

    # --- Hospital → Booking/Appointment Workflow ---
    def test_hospital_generates_booking_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_005", "Apollo Hospital", "hospital", []
        )
        assert "Booking Workflow" in portfolio or "Appointment Workflow" in portfolio

    # --- Clinic → Booking/Appointment Workflow ---
    def test_clinic_generates_booking_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_006", "City Clinic", "clinic", []
        )
        assert "Booking Workflow" in portfolio or "Appointment Workflow" in portfolio

    # --- Gym → Booking Workflow ---
    def test_gym_generates_booking_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_007", "TitanFit", "gym", []
        )
        assert "Booking Workflow" in portfolio

    # --- Unknown → General Service ---
    def test_unknown_category_generates_general_service(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_008", "Random Biz", "unknowncategory", []
        )
        assert "General Service" in portfolio
        assert "Ordering Workflow" not in portfolio
        assert "Booking Workflow" not in portfolio

    # --- Every portfolio must include Support and Feedback ---
    def test_restaurant_portfolio_has_support_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_001", "Pizza Planet", "restaurant", []
        )
        assert "Support Workflow" in portfolio

    def test_restaurant_portfolio_has_feedback_workflow(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_001", "Pizza Planet", "restaurant", []
        )
        assert "Feedback Workflow" in portfolio

    def test_salon_portfolio_has_support_and_feedback(self):
        portfolio = AIGenerator.build_programmatic_portfolio(
            "biz_004", "Luxe Salon", "salon", []
        )
        assert "Support Workflow" in portfolio
        assert "Feedback Workflow" in portfolio


# ---------------------------------------------------------------------------
# Section 4 — Feedback trigger event (Fix 2 + Spec Section M)
# ---------------------------------------------------------------------------

class TestFeedbackWorkflowTrigger:

    def test_restaurant_feedback_triggers_on_delivery_completed(self):
        wf = AIGenerator.get_feedback_workflow("biz_001", "Pizza Planet", "restaurant")
        assert wf["trigger_event"] == "DELIVERY_COMPLETED", (
            f"Restaurant feedback must trigger on DELIVERY_COMPLETED, got '{wf['trigger_event']}'"
        )

    def test_ecommerce_feedback_triggers_on_delivery_completed(self):
        wf = AIGenerator.get_feedback_workflow("biz_002", "ShopZone", "ecommerce")
        assert wf["trigger_event"] == "DELIVERY_COMPLETED"

    def test_salon_feedback_triggers_on_booking_confirmed(self):
        wf = AIGenerator.get_feedback_workflow("biz_004", "Luxe Salon", "salon")
        assert wf["trigger_event"] == "BOOKING_CONFIRMED", (
            f"Salon feedback must trigger on BOOKING_CONFIRMED, got '{wf['trigger_event']}'"
        )

    def test_hospital_feedback_triggers_on_booking_confirmed(self):
        wf = AIGenerator.get_feedback_workflow("biz_005", "Apollo Hospital", "hospital")
        assert wf["trigger_event"] == "BOOKING_CONFIRMED"

    def test_clinic_feedback_triggers_on_booking_confirmed(self):
        wf = AIGenerator.get_feedback_workflow("biz_006", "City Clinic", "clinic")
        assert wf["trigger_event"] == "BOOKING_CONFIRMED"

    def test_gym_feedback_triggers_on_booking_confirmed(self):
        wf = AIGenerator.get_feedback_workflow("biz_007", "TitanFit", "gym")
        assert wf["trigger_event"] == "BOOKING_CONFIRMED"


# ---------------------------------------------------------------------------
# Section 5 — Ordering Workflow structure (restaurant — no haircut content)
# ---------------------------------------------------------------------------

class TestOrderingWorkflowContent:

    def test_restaurant_ordering_has_full_delivery_chain(self):
        wf = AIGenerator.get_ordering_workflow("biz_001", "Pizza Planet", "restaurant", [])
        modules = [n["module_name"] for n in wf["nodes"].values()]
        assert "show_menu"       in modules
        assert "collect_cart"    in modules
        assert "calculate_total" in modules
        assert "create_order"    in modules
        assert "create_payment"  in modules
        assert "confirm_payment" in modules
        assert "collect_address" in modules
        assert "create_delivery" in modules
        assert "notify_customer" in modules

    def test_restaurant_menu_has_no_haircut_content(self):
        """The single most important regression check — no salon content in restaurant flow."""
        wf = AIGenerator.get_ordering_workflow("biz_001", "Pizza Planet", "restaurant", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"].lower()
        assert "haircut"  not in menu_text, "REGRESSION: salon content in restaurant ordering workflow"
        assert "hair wash" not in menu_text, "REGRESSION: salon content in restaurant ordering workflow"
        assert "styling"  not in menu_text, "REGRESSION: salon content in restaurant ordering workflow"

    def test_pharmacy_ordering_has_medicine_defaults(self):
        wf = AIGenerator.get_ordering_workflow("biz_003", "MediPlus", "pharmacy", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert "Cough Syrup" in menu_text or "Pain Reliever" in menu_text

    def test_restaurant_ordering_fsm_table_complete(self):
        wf = AIGenerator.get_ordering_workflow("biz_001", "Pizza Planet", "restaurant", [])
        table = wf["fsm_transition_table"]
        assert "START"    in table
        assert "MENU"     in table
        assert "CART"     in table
        assert "CHECKOUT" in table
        assert "PAYMENT"  in table


# ---------------------------------------------------------------------------
# Section 6 — Booking Workflow: correct defaults per sub-category (Fix 2)
# ---------------------------------------------------------------------------

class TestBookingWorkflowDefaults:

    def test_salon_has_haircut_content(self):
        wf = AIGenerator.get_booking_workflow("biz_004", "Luxe Salon", "salon", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert "Haircut" in menu_text

    def test_clinic_has_consultation_content(self):
        wf = AIGenerator.get_booking_workflow("biz_006", "City Clinic", "clinic", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert "Consultation" in menu_text or "consultation" in menu_text.lower()

    def test_hospital_has_consultation_content(self):
        wf = AIGenerator.get_booking_workflow("biz_005", "Apollo Hospital", "hospital", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert "Consultation" in menu_text or "consultation" in menu_text.lower()

    def test_gym_has_membership_content(self):
        wf = AIGenerator.get_booking_workflow("biz_007", "TitanFit", "gym", [])
        menu_text = wf["nodes"]["node_menu"]["config"]["menu_header"]
        assert "Membership" in menu_text or "membership" in menu_text.lower()


# ---------------------------------------------------------------------------
# Section 7 — Category constant sets are internally consistent
# ---------------------------------------------------------------------------

class TestCategoryConstants:

    def test_ordering_categories_are_correct(self):
        assert CAT_RESTAURANT in ORDERING_CATEGORIES
        assert CAT_ECOMMERCE  in ORDERING_CATEGORIES
        assert CAT_PHARMACY   in ORDERING_CATEGORIES

    def test_booking_categories_are_correct(self):
        assert CAT_SALON      in BOOKING_CATEGORIES
        assert CAT_CLINIC     in BOOKING_CATEGORIES
        assert CAT_HOSPITAL   in BOOKING_CATEGORIES
        assert CAT_GYM        in BOOKING_CATEGORIES
        assert CAT_HOTEL      in BOOKING_CATEGORIES
        assert CAT_TRAVEL     in BOOKING_CATEGORIES
        assert CAT_REALESTATE in BOOKING_CATEGORIES

    def test_no_overlap_between_ordering_and_booking(self):
        overlap = ORDERING_CATEGORIES & BOOKING_CATEGORIES
        assert not overlap, f"Categories appear in both sets: {overlap}"

    def test_delivery_feedback_is_subset_of_ordering(self):
        assert DELIVERY_FEEDBACK_CATEGORIES.issubset(ORDERING_CATEGORIES)

    def test_salon_not_in_delivery_feedback(self):
        assert CAT_SALON not in DELIVERY_FEEDBACK_CATEGORIES

    def test_hospital_not_in_delivery_feedback(self):
        assert CAT_HOSPITAL not in DELIVERY_FEEDBACK_CATEGORIES
