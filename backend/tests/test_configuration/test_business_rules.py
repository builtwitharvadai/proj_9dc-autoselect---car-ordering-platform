"""
Comprehensive test suite for configuration business rules engine.

Tests cover option compatibility validation, package eligibility, required options
checking, mutually exclusive option detection, and all edge cases with proper
error handling and validation.
"""

import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.configuration.business_rules import (
    ConfigurationRulesEngine,
    ConfigurationValidationError,
)
from src.database.models.vehicle_option import VehicleOption
from src.database.models.package import Package


# ============================================================================
# Test Fixtures and Factories
# ============================================================================


@pytest.fixture
def mock_session():
    """Create mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def rules_engine(mock_session):
    """Create configuration rules engine with mock session."""
    return ConfigurationRulesEngine(session=mock_session)


@pytest.fixture
def vehicle_id():
    """Generate test vehicle ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_options(vehicle_id):
    """Create sample vehicle options for testing."""
    return [
        VehicleOption(
            id=uuid.uuid4(),
            vehicle_id=vehicle_id,
            name="Premium Audio",
            category="audio",
            price=Decimal("1500.00"),
            is_required=False,
            mutually_exclusive_with=[],
            required_options=[],
        ),
        VehicleOption(
            id=uuid.uuid4(),
            vehicle_id=vehicle_id,
            name="Leather Seats",
            category="interior",
            price=Decimal("2000.00"),
            is_required=True,
            mutually_exclusive_with=[],
            required_options=[],
        ),
        VehicleOption(
            id=uuid.uuid4(),
            vehicle_id=vehicle_id,
            name="Sport Package",
            category="performance",
            price=Decimal("3000.00"),
            is_required=False,
            mutually_exclusive_with=[],
            required_options=[],
        ),
    ]


@pytest.fixture
def sample_packages(vehicle_id, sample_options):
    """Create sample packages for testing."""
    return [
        Package(
            id=uuid.uuid4(),
            vehicle_id=vehicle_id,
            name="Luxury Package",
            description="Premium luxury features",
            price=Decimal("5000.00"),
            included_options=[sample_options[0].id, sample_options[1].id],
            compatible_trims=["Premium", "Luxury"],
            compatible_years=[2024, 2025],
        ),
        Package(
            id=uuid.uuid4(),
            vehicle_id=vehicle_id,
            name="Sport Package",
            description="Performance enhancements",
            price=Decimal("4000.00"),
            included_options=[sample_options[2].id],
            compatible_trims=["Sport", "Premium"],
            compatible_years=[2024],
        ),
    ]


# ============================================================================
# Unit Tests: ConfigurationValidationError
# ============================================================================


class TestConfigurationValidationError:
    """Test suite for ConfigurationValidationError exception."""

    def test_error_initialization_with_all_fields(self, vehicle_id):
        """Test error initialization with all fields."""
        errors = ["Error 1", "Error 2"]
        context = {"field": "value"}

        error = ConfigurationValidationError(
            message="Validation failed",
            errors=errors,
            vehicle_id=vehicle_id,
            **context,
        )

        assert str(error) == "Validation failed"
        assert error.errors == errors
        assert error.vehicle_id == vehicle_id
        assert error.context == context

    def test_error_initialization_minimal(self):
        """Test error initialization with minimal fields."""
        errors = ["Single error"]

        error = ConfigurationValidationError(
            message="Failed",
            errors=errors,
        )

        assert str(error) == "Failed"
        assert error.errors == errors
        assert error.vehicle_id is None
        assert error.context == {}

    def test_error_with_empty_errors_list(self):
        """Test error with empty errors list."""
        error = ConfigurationValidationError(
            message="No specific errors",
            errors=[],
        )

        assert error.errors == []
        assert len(error.errors) == 0


# ============================================================================
# Unit Tests: ConfigurationRulesEngine Initialization
# ============================================================================


class TestConfigurationRulesEngineInit:
    """Test suite for ConfigurationRulesEngine initialization."""

    def test_engine_initialization(self, mock_session):
        """Test successful engine initialization."""
        engine = ConfigurationRulesEngine(session=mock_session)

        assert engine.session == mock_session

    @patch("src.services.configuration.business_rules.logger")
    def test_engine_initialization_logs(self, mock_logger, mock_session):
        """Test that initialization logs correctly."""
        ConfigurationRulesEngine(session=mock_session)

        mock_logger.info.assert_called_once_with(
            "Configuration rules engine initialized"
        )


# ============================================================================
# Unit Tests: Required Options Validation
# ============================================================================


class TestCheckRequiredOptions:
    """Test suite for required options validation."""

    @pytest.mark.asyncio
    async def test_all_required_options_selected(
        self, rules_engine, sample_options
    ):
        """Test validation passes when all required options are selected."""
        required_option = sample_options[1]  # Leather Seats (required)
        selected_ids = [required_option.id]

        errors = await rules_engine.check_required_options(
            sample_options, selected_ids
        )

        assert errors == []

    @pytest.mark.asyncio
    async def test_missing_required_option(self, rules_engine, sample_options):
        """Test validation fails when required option is missing."""
        required_option = sample_options[1]  # Leather Seats (required)
        selected_ids = [sample_options[0].id]  # Only Premium Audio

        errors = await rules_engine.check_required_options(
            sample_options, selected_ids
        )

        assert len(errors) == 1
        assert "Leather Seats" in errors[0]
        assert "must be selected" in errors[0]
        assert "interior" in errors[0]

    @pytest.mark.asyncio
    async def test_no_required_options(self, rules_engine, vehicle_id):
        """Test validation passes when no options are required."""
        options = [
            VehicleOption(
                id=uuid.uuid4(),
                vehicle_id=vehicle_id,
                name="Optional Feature",
                category="misc",
                price=Decimal("500.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[],
            )
        ]

        errors = await rules_engine.check_required_options(options, [])

        assert errors == []

    @pytest.mark.asyncio
    async def test_multiple_missing_required_options(
        self, rules_engine, vehicle_id
    ):
        """Test validation reports all missing required options."""
        options = [
            VehicleOption(
                id=uuid.uuid4(),
                vehicle_id=vehicle_id,
                name="Required 1",
                category="cat1",
                price=Decimal("100.00"),
                is_required=True,
                mutually_exclusive_with=[],
                required_options=[],
            ),
            VehicleOption(
                id=uuid.uuid4(),
                vehicle_id=vehicle_id,
                name="Required 2",
                category="cat2",
                price=Decimal("200.00"),
                is_required=True,
                mutually_exclusive_with=[],
                required_options=[],
            ),
        ]

        errors = await rules_engine.check_required_options(options, [])

        assert len(errors) == 2
        assert any("Required 1" in error for error in errors)
        assert any("Required 2" in error for error in errors)


# ============================================================================
# Unit Tests: Mutually Exclusive Options
# ============================================================================


class TestCheckMutuallyExclusive:
    """Test suite for mutually exclusive options validation."""

    @pytest.mark.asyncio
    async def test_no_conflicts(self, rules_engine, sample_options):
        """Test validation passes when no conflicts exist."""
        selected_ids = [sample_options[0].id, sample_options[1].id]

        errors = await rules_engine.check_mutually_exclusive(
            sample_options, selected_ids
        )

        assert errors == []

    @pytest.mark.asyncio
    async def test_mutually_exclusive_conflict(self, rules_engine, vehicle_id):
        """Test validation fails when mutually exclusive options selected."""
        option1_id = uuid.uuid4()
        option2_id = uuid.uuid4()

        options = [
            VehicleOption(
                id=option1_id,
                vehicle_id=vehicle_id,
                name="Manual Transmission",
                category="transmission",
                price=Decimal("0.00"),
                is_required=False,
                mutually_exclusive_with=[option2_id],
                required_options=[],
            ),
            VehicleOption(
                id=option2_id,
                vehicle_id=vehicle_id,
                name="Automatic Transmission",
                category="transmission",
                price=Decimal("1500.00"),
                is_required=False,
                mutually_exclusive_with=[option1_id],
                required_options=[],
            ),
        ]

        selected_ids = [option1_id, option2_id]

        errors = await rules_engine.check_mutually_exclusive(
            options, selected_ids
        )

        assert len(errors) >= 1
        assert any("mutually exclusive" in error for error in errors)

    @pytest.mark.asyncio
    async def test_no_mutually_exclusive_options(
        self, rules_engine, sample_options
    ):
        """Test validation with options that have no exclusivity rules."""
        selected_ids = [opt.id for opt in sample_options]

        errors = await rules_engine.check_mutually_exclusive(
            sample_options, selected_ids
        )

        assert errors == []

    @pytest.mark.asyncio
    async def test_exclusive_option_not_selected(
        self, rules_engine, vehicle_id
    ):
        """Test no conflict when exclusive option is not selected."""
        option1_id = uuid.uuid4()
        option2_id = uuid.uuid4()

        options = [
            VehicleOption(
                id=option1_id,
                vehicle_id=vehicle_id,
                name="Option 1",
                category="cat1",
                price=Decimal("100.00"),
                is_required=False,
                mutually_exclusive_with=[option2_id],
                required_options=[],
            ),
            VehicleOption(
                id=option2_id,
                vehicle_id=vehicle_id,
                name="Option 2",
                category="cat2",
                price=Decimal("200.00"),
                is_required=False,
                mutually_exclusive_with=[option1_id],
                required_options=[],
            ),
        ]

        selected_ids = [option1_id]  # Only select one

        errors = await rules_engine.check_mutually_exclusive(
            options, selected_ids
        )

        assert errors == []


# ============================================================================
# Unit Tests: Option Dependencies
# ============================================================================


class TestCheckOptionDependencies:
    """Test suite for option dependency validation."""

    @pytest.mark.asyncio
    async def test_all_dependencies_satisfied(
        self, rules_engine, vehicle_id
    ):
        """Test validation passes when all dependencies are met."""
        dep_option_id = uuid.uuid4()
        main_option_id = uuid.uuid4()

        options = [
            VehicleOption(
                id=dep_option_id,
                vehicle_id=vehicle_id,
                name="Base Feature",
                category="base",
                price=Decimal("500.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[],
            ),
            VehicleOption(
                id=main_option_id,
                vehicle_id=vehicle_id,
                name="Advanced Feature",
                category="advanced",
                price=Decimal("1000.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[dep_option_id],
            ),
        ]

        selected_ids = [dep_option_id, main_option_id]

        errors = await rules_engine.check_option_dependencies(
            options, selected_ids
        )

        assert errors == []

    @pytest.mark.asyncio
    async def test_missing_dependency(self, rules_engine, vehicle_id):
        """Test validation fails when dependency is missing."""
        dep_option_id = uuid.uuid4()
        main_option_id = uuid.uuid4()

        options = [
            VehicleOption(
                id=dep_option_id,
                vehicle_id=vehicle_id,
                name="Required Base",
                category="base",
                price=Decimal("500.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[],
            ),
            VehicleOption(
                id=main_option_id,
                vehicle_id=vehicle_id,
                name="Dependent Feature",
                category="advanced",
                price=Decimal("1000.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[dep_option_id],
            ),
        ]

        selected_ids = [main_option_id]  # Missing dependency

        errors = await rules_engine.check_option_dependencies(
            options, selected_ids
        )

        assert len(errors) == 1
        assert "Dependent Feature" in errors[0]
        assert "requires" in errors[0]
        assert "Required Base" in errors[0]

    @pytest.mark.asyncio
    async def test_no_dependencies(self, rules_engine, sample_options):
        """Test validation with options that have no dependencies."""
        selected_ids = [sample_options[0].id]

        errors = await rules_engine.check_option_dependencies(
            sample_options, selected_ids
        )

        assert errors == []

    @pytest.mark.asyncio
    async def test_multiple_missing_dependencies(
        self, rules_engine, vehicle_id
    ):
        """Test validation reports all missing dependencies."""
        dep1_id = uuid.uuid4()
        dep2_id = uuid.uuid4()
        main_id = uuid.uuid4()

        options = [
            VehicleOption(
                id=dep1_id,
                vehicle_id=vehicle_id,
                name="Dependency 1",
                category="cat1",
                price=Decimal("100.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[],
            ),
            VehicleOption(
                id=dep2_id,
                vehicle_id=vehicle_id,
                name="Dependency 2",
                category="cat2",
                price=Decimal("200.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[],
            ),
            VehicleOption(
                id=main_id,
                vehicle_id=vehicle_id,
                name="Main Feature",
                category="main",
                price=Decimal("1000.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[dep1_id, dep2_id],
            ),
        ]

        selected_ids = [main_id]

        errors = await rules_engine.check_option_dependencies(
            options, selected_ids
        )

        assert len(errors) == 2
        assert any("Dependency 1" in error for error in errors)
        assert any("Dependency 2" in error for error in errors)


# ============================================================================
# Unit Tests: Package Requirements
# ============================================================================


class TestValidatePackageRequirements:
    """Test suite for package requirements validation."""

    @pytest.mark.asyncio
    async def test_all_package_options_selected(
        self, rules_engine, sample_packages, sample_options
    ):
        """Test validation passes when all package options are selected."""
        package = sample_packages[0]
        selected_package_ids = [package.id]
        selected_option_ids = [sample_options[0].id, sample_options[1].id]

        errors = await rules_engine.validate_package_requirements(
            sample_packages, selected_package_ids, selected_option_ids
        )

        assert errors == []

    @pytest.mark.asyncio
    async def test_missing_package_options(
        self, rules_engine, sample_packages, sample_options
    ):
        """Test validation fails when package options are missing."""
        package = sample_packages[0]
        selected_package_ids = [package.id]
        selected_option_ids = [sample_options[0].id]  # Missing one option

        errors = await rules_engine.validate_package_requirements(
            sample_packages, selected_package_ids, selected_option_ids
        )

        assert len(errors) == 1
        assert "Luxury Package" in errors[0]
        assert "requires all included options" in errors[0]

    @pytest.mark.asyncio
    async def test_no_packages_selected(
        self, rules_engine, sample_packages, sample_options
    ):
        """Test validation passes when no packages are selected."""
        errors = await rules_engine.validate_package_requirements(
            sample_packages, [], [sample_options[0].id]
        )

        assert errors == []

    @pytest.mark.asyncio
    async def test_multiple_packages_with_mixed_validity(
        self, rules_engine, sample_packages, sample_options
    ):
        """Test validation with multiple packages, some valid, some invalid."""
        selected_package_ids = [pkg.id for pkg in sample_packages]
        # Only include options for first package
        selected_option_ids = [sample_options[0].id, sample_options[1].id]

        errors = await rules_engine.validate_package_requirements(
            sample_packages, selected_package_ids, selected_option_ids
        )

        # Second package should fail (missing Sport Package option)
        assert len(errors) >= 1
        assert any("Sport Package" in error for error in errors)


# ============================================================================
# Unit Tests: Package Compatibility
# ============================================================================


class TestValidatePackageCompatibility:
    """Test suite for package compatibility validation."""

    @pytest.mark.asyncio
    async def test_compatible_trim_and_year(
        self, rules_engine, sample_packages
    ):
        """Test validation passes for compatible trim and year."""
        package = sample_packages[0]
        selected_package_ids = [package.id]

        with patch.object(
            package, "validate_compatibility", return_value=(True, [])
        ):
            errors = await rules_engine.validate_package_compatibility(
                sample_packages, selected_package_ids, "Premium", 2024
            )

        assert errors == []

    @pytest.mark.asyncio
    async def test_incompatible_trim(self, rules_engine, sample_packages):
        """Test validation fails for incompatible trim."""
        package = sample_packages[0]
        selected_package_ids = [package.id]
        compatibility_errors = ["Package not compatible with Base trim"]

        with patch.object(
            package,
            "validate_compatibility",
            return_value=(False, compatibility_errors),
        ):
            errors = await rules_engine.validate_package_compatibility(
                sample_packages, selected_package_ids, "Base", 2024
            )

        assert len(errors) == 1
        assert "not compatible" in errors[0]

    @pytest.mark.asyncio
    async def test_incompatible_year(self, rules_engine, sample_packages):
        """Test validation fails for incompatible year."""
        package = sample_packages[0]
        selected_package_ids = [package.id]
        compatibility_errors = ["Package not available for year 2023"]

        with patch.object(
            package,
            "validate_compatibility",
            return_value=(False, compatibility_errors),
        ):
            errors = await rules_engine.validate_package_compatibility(
                sample_packages, selected_package_ids, "Premium", 2023
            )

        assert len(errors) == 1
        assert "not available" in errors[0]

    @pytest.mark.asyncio
    async def test_no_trim_or_year_specified(
        self, rules_engine, sample_packages
    ):
        """Test validation with no trim or year specified."""
        package = sample_packages[0]
        selected_package_ids = [package.id]

        with patch.object(
            package, "validate_compatibility", return_value=(True, [])
        ):
            errors = await rules_engine.validate_package_compatibility(
                sample_packages, selected_package_ids, None, None
            )

        assert errors == []


# ============================================================================
# Unit Tests: Configuration Completeness
# ============================================================================


class TestValidateConfigurationCompleteness:
    """Test suite for configuration completeness validation."""

    @pytest.mark.asyncio
    async def test_valid_complete_configuration(
        self, rules_engine, sample_options
    ):
        """Test validation passes for complete valid configuration."""
        selected_option_ids = [sample_options[0].id]
        selected_package_ids = []

        errors = await rules_engine.validate_configuration_completeness(
            sample_options, selected_option_ids, selected_package_ids
        )

        assert errors == []

    @pytest.mark.asyncio
    async def test_empty_configuration(self, rules_engine, sample_options):
        """Test validation fails for empty configuration."""
        errors = await rules_engine.validate_configuration_completeness(
            sample_options, [], []
        )

        assert len(errors) == 1
        assert "at least one option or package" in errors[0]

    @pytest.mark.asyncio
    async def test_duplicate_option_selections(
        self, rules_engine, sample_options
    ):
        """Test validation fails for duplicate option selections."""
        option_id = sample_options[0].id
        selected_option_ids = [option_id, option_id]  # Duplicate

        errors = await rules_engine.validate_configuration_completeness(
            sample_options, selected_option_ids, []
        )

        assert len(errors) == 1
        assert "duplicate option selections" in errors[0]

    @pytest.mark.asyncio
    async def test_duplicate_package_selections(
        self, rules_engine, sample_options
    ):
        """Test validation fails for duplicate package selections."""
        package_id = uuid.uuid4()
        selected_package_ids = [package_id, package_id]  # Duplicate

        errors = await rules_engine.validate_configuration_completeness(
            sample_options, [sample_options[0].id], selected_package_ids
        )

        assert len(errors) == 1
        assert "duplicate package selections" in errors[0]

    @pytest.mark.asyncio
    async def test_invalid_option_ids(self, rules_engine, sample_options):
        """Test validation fails for invalid option IDs."""
        invalid_id = uuid.uuid4()
        selected_option_ids = [sample_options[0].id, invalid_id]

        errors = await rules_engine.validate_configuration_completeness(
            sample_options, selected_option_ids, []
        )

        assert len(errors) == 1
        assert "invalid option IDs" in errors[0]
        assert str(invalid_id) in errors[0]

    @pytest.mark.asyncio
    async def test_multiple_completeness_issues(
        self, rules_engine, sample_options
    ):
        """Test validation reports multiple completeness issues."""
        option_id = sample_options[0].id
        invalid_id = uuid.uuid4()
        selected_option_ids = [option_id, option_id, invalid_id]  # Dup + invalid

        errors = await rules_engine.validate_configuration_completeness(
            sample_options, selected_option_ids, []
        )

        assert len(errors) == 2
        assert any("duplicate" in error for error in errors)
        assert any("invalid" in error for error in errors)


# ============================================================================
# Integration Tests: Complete Configuration Validation
# ============================================================================


class TestValidateConfiguration:
    """Integration test suite for complete configuration validation."""

    @pytest.mark.asyncio
    async def test_valid_complete_configuration(
        self, rules_engine, vehicle_id, sample_options, sample_packages
    ):
        """Test successful validation of complete valid configuration."""
        rules_engine._load_vehicle_options = AsyncMock(
            return_value=sample_options
        )
        rules_engine._load_vehicle_packages = AsyncMock(
            return_value=sample_packages
        )

        selected_option_ids = [opt.id for opt in sample_options]
        selected_package_ids = []

        is_valid, errors = await rules_engine.validate_configuration(
            vehicle_id, selected_option_ids, selected_package_ids
        )

        assert is_valid is True
        assert errors == []

    @pytest.mark.asyncio
    async def test_no_options_found_for_vehicle(
        self, rules_engine, vehicle_id
    ):
        """Test validation fails when no options exist for vehicle."""
        rules_engine._load_vehicle_options = AsyncMock(return_value=[])
        rules_engine._load_vehicle_packages = AsyncMock(return_value=[])

        is_valid, errors = await rules_engine.validate_configuration(
            vehicle_id, [], []
        )

        assert is_valid is False
        assert len(errors) == 1
        assert "No options found" in errors[0]

    @pytest.mark.asyncio
    async def test_multiple_validation_failures(
        self, rules_engine, vehicle_id, sample_options
    ):
        """Test validation reports multiple failures."""
        rules_engine._load_vehicle_options = AsyncMock(
            return_value=sample_options
        )
        rules_engine._load_vehicle_packages = AsyncMock(return_value=[])

        # Empty configuration (missing required option)
        is_valid, errors = await rules_engine.validate_configuration(
            vehicle_id, [], []
        )

        assert is_valid is False
        assert len(errors) >= 2  # Missing required + empty config

    @pytest.mark.asyncio
    async def test_configuration_with_packages(
        self, rules_engine, vehicle_id, sample_options, sample_packages
    ):
        """Test validation with packages included."""
        rules_engine._load_vehicle_options = AsyncMock(
            return_value=sample_options
        )
        rules_engine._load_vehicle_packages = AsyncMock(
            return_value=sample_packages
        )

        package = sample_packages[0]
        selected_option_ids = [opt.id for opt in sample_options]
        selected_package_ids = [package.id]

        with patch.object(
            package, "validate_compatibility", return_value=(True, [])
        ):
            is_valid, errors = await rules_engine.validate_configuration(
                vehicle_id,
                selected_option_ids,
                selected_package_ids,
                trim="Premium",
                year=2024,
            )

        assert is_valid is True
        assert errors == []

    @pytest.mark.asyncio
    async def test_configuration_with_trim_and_year(
        self, rules_engine, vehicle_id, sample_options, sample_packages
    ):
        """Test validation includes trim and year compatibility."""
        rules_engine._load_vehicle_options = AsyncMock(
            return_value=sample_options
        )
        rules_engine._load_vehicle_packages = AsyncMock(
            return_value=sample_packages
        )

        package = sample_packages[0]
        selected_option_ids = [opt.id for opt in sample_options]
        selected_package_ids = [package.id]

        compatibility_errors = ["Incompatible with trim"]
        with patch.object(
            package,
            "validate_compatibility",
            return_value=(False, compatibility_errors),
        ):
            is_valid, errors = await rules_engine.validate_configuration(
                vehicle_id,
                selected_option_ids,
                selected_package_ids,
                trim="Base",
                year=2023,
            )

        assert is_valid is False
        assert any("Incompatible" in error for error in errors)


# ============================================================================
# Integration Tests: Package Eligibility
# ============================================================================


class TestValidatePackageEligibility:
    """Integration test suite for package eligibility validation."""

    @pytest.mark.asyncio
    async def test_eligible_package(
        self, rules_engine, vehicle_id, sample_packages
    ):
        """Test validation passes for eligible package."""
        package = sample_packages[0]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = package
        rules_engine.session.execute = AsyncMock(return_value=mock_result)

        with patch.object(
            package, "validate_compatibility", return_value=(True, [])
        ):
            is_eligible, errors = await rules_engine.validate_package_eligibility(
                vehicle_id, package.id, "Premium", 2024
            )

        assert is_eligible is True
        assert errors == []

    @pytest.mark.asyncio
    async def test_package_not_found(self, rules_engine, vehicle_id):
        """Test validation fails when package not found."""
        package_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        rules_engine.session.execute = AsyncMock(return_value=mock_result)

        is_eligible, errors = await rules_engine.validate_package_eligibility(
            vehicle_id, package_id
        )

        assert is_eligible is False
        assert len(errors) == 1
        assert "not found" in errors[0]

    @pytest.mark.asyncio
    async def test_ineligible_package(
        self, rules_engine, vehicle_id, sample_packages
    ):
        """Test validation fails for ineligible package."""
        package = sample_packages[0]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = package
        rules_engine.session.execute = AsyncMock(return_value=mock_result)

        compatibility_errors = ["Not compatible with Base trim"]
        with patch.object(
            package,
            "validate_compatibility",
            return_value=(False, compatibility_errors),
        ):
            is_eligible, errors = await rules_engine.validate_package_eligibility(
                vehicle_id, package.id, "Base", 2024
            )

        assert is_eligible is False
        assert len(errors) == 1
        assert "Not compatible" in errors[0]


# ============================================================================
# Unit Tests: Private Helper Methods
# ============================================================================


class TestPrivateHelperMethods:
    """Test suite for private helper methods."""

    @pytest.mark.asyncio
    async def test_load_vehicle_options(
        self, rules_engine, vehicle_id, sample_options
    ):
        """Test loading vehicle options from database."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_options
        rules_engine.session.execute = AsyncMock(return_value=mock_result)

        options = await rules_engine._load_vehicle_options(vehicle_id)

        assert len(options) == len(sample_options)
        assert options == sample_options

    @pytest.mark.asyncio
    async def test_load_vehicle_options_empty(
        self, rules_engine, vehicle_id
    ):
        """Test loading vehicle options when none exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        rules_engine.session.execute = AsyncMock(return_value=mock_result)

        options = await rules_engine._load_vehicle_options(vehicle_id)

        assert options == []

    @pytest.mark.asyncio
    async def test_load_vehicle_packages(
        self, rules_engine, vehicle_id, sample_packages
    ):
        """Test loading vehicle packages from database."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_packages
        rules_engine.session.execute = AsyncMock(return_value=mock_result)

        packages = await rules_engine._load_vehicle_packages(vehicle_id)

        assert len(packages) == len(sample_packages)
        assert packages == sample_packages

    @pytest.mark.asyncio
    async def test_load_vehicle_packages_empty(
        self, rules_engine, vehicle_id
    ):
        """Test loading vehicle packages when none exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        rules_engine.session.execute = AsyncMock(return_value=mock_result)

        packages = await rules_engine._load_vehicle_packages(vehicle_id)

        assert packages == []


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


class TestEdgeCasesAndErrors:
    """Test suite for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_validation_with_none_values(
        self, rules_engine, vehicle_id, sample_options
    ):
        """Test validation handles None values gracefully."""
        rules_engine._load_vehicle_options = AsyncMock(
            return_value=sample_options
        )
        rules_engine._load_vehicle_packages = AsyncMock(return_value=[])

        is_valid, errors = await rules_engine.validate_configuration(
            vehicle_id,
            [sample_options[0].id],
            [],
            trim=None,
            year=None,
        )

        # Should still validate other aspects
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    @pytest.mark.asyncio
    async def test_validation_with_large_option_list(
        self, rules_engine, vehicle_id
    ):
        """Test validation performance with large option list."""
        # Create 100 options
        large_option_list = [
            VehicleOption(
                id=uuid.uuid4(),
                vehicle_id=vehicle_id,
                name=f"Option {i}",
                category="test",
                price=Decimal("100.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[],
            )
            for i in range(100)
        ]

        rules_engine._load_vehicle_options = AsyncMock(
            return_value=large_option_list
        )
        rules_engine._load_vehicle_packages = AsyncMock(return_value=[])

        selected_ids = [opt.id for opt in large_option_list[:50]]

        is_valid, errors = await rules_engine.validate_configuration(
            vehicle_id, selected_ids, []
        )

        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    @pytest.mark.asyncio
    async def test_circular_dependencies_detection(
        self, rules_engine, vehicle_id
    ):
        """Test handling of circular option dependencies."""
        option1_id = uuid.uuid4()
        option2_id = uuid.uuid4()

        options = [
            VehicleOption(
                id=option1_id,
                vehicle_id=vehicle_id,
                name="Option 1",
                category="cat1",
                price=Decimal("100.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[option2_id],
            ),
            VehicleOption(
                id=option2_id,
                vehicle_id=vehicle_id,
                name="Option 2",
                category="cat2",
                price=Decimal("200.00"),
                is_required=False,
                mutually_exclusive_with=[],
                required_options=[option1_id],
            ),
        ]

        # Both selected - should pass (circular but both present)
        errors = await rules_engine.check_option_dependencies(
            options, [option1_id, option2_id]
        )

        assert errors == []

    @pytest.mark.asyncio
    async def test_validation_with_special_characters_in_names(
        self, rules_engine, vehicle_id
    ):
        """Test validation handles special characters in option names."""
        options = [
            VehicleOption(
                id=uuid.uuid4(),
                vehicle_id=vehicle_id,
                name="Option with 'quotes' & <special> chars",
                category="test",
                price=Decimal("100.00"),
                is_required=True,
                mutually_exclusive_with=[],
                required_options=[],
            )
        ]

        errors = await rules_engine.check_required_options(options, [])

        assert len(errors) == 1
        assert "Option with 'quotes' & <special> chars" in errors[0]


# ============================================================================
# Performance and Stress Tests
# ============================================================================


class TestPerformanceAndStress:
    """Test suite for performance and stress scenarios."""

    @pytest.mark.asyncio
    async def test_validation_performance_baseline(
        self, rules_engine, vehicle_id, sample_options
    ):
        """Test baseline performance of validation."""
        import time

        rules_engine._load_vehicle_options = AsyncMock(
            return_value=sample_options
        )
        rules_engine._load_vehicle_packages = AsyncMock(return_value=[])

        start_time = time.time()

        await rules_engine.validate_configuration(
            vehicle_id, [sample_options[0].id], []
        )

        elapsed_time = time.time() - start_time

        # Should complete in reasonable time (< 1 second)
        assert elapsed_time < 1.0

    @pytest.mark.asyncio
    async def test_concurrent_validations(
        self, rules_engine, vehicle_id, sample_options
    ):
        """Test handling of concurrent validation requests."""
        import asyncio

        rules_engine._load_vehicle_options = AsyncMock(
            return_value=sample_options
        )
        rules_engine._load_vehicle_packages = AsyncMock(return_value=[])

        # Run 10 concurrent validations
        tasks = [
            rules_engine.validate_configuration(
                vehicle_id, [sample_options[0].id], []
            )
            for _ in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(is_valid for is_valid, _ in results)