"""
Robust PostgreSQL Partition Management for Alembic Migrations.

This module provides a complete solution for automatic partition management
including detection, validation, SQL generation, and integration with Alembic.
"""

# Standard library imports
from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from typing import Any, cast

# Third-party imports
from sqlalchemy import MetaData, Table

# Configure logging
logger = logging.getLogger(__name__)


class PartitionStrategy(Enum):
    """Supported partitioning strategies."""

    HASH = "HASH"
    RANGE = "RANGE"
    LIST = "LIST"


class PartitionError(Exception):
    """Base exception for partition-related errors."""

    pass


class PartitionConfigError(PartitionError):
    """Exception raised for invalid partition configurations."""

    pass


class PartitionSQLError(PartitionError):
    """Exception raised for SQL generation errors."""

    pass


@dataclass
class PartitionConfig:
    """Configuration for a partitioned table."""

    table_name: str
    strategy: PartitionStrategy
    column: str
    partition_count: int = 4
    naming_pattern: str = "{table}_p{number}"
    custom_values: list[Any] | None = None
    range_bounds: list[tuple[Any, Any]] | None = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate the partition configuration."""
        if self.partition_count < 1:
            raise PartitionConfigError(f"Partition count must be >= 1, got {self.partition_count}")

        if self.strategy == PartitionStrategy.RANGE and not self.range_bounds:
            raise PartitionConfigError("RANGE partitioning requires range_bounds to be specified")

        if self.strategy == PartitionStrategy.LIST and not self.custom_values:
            raise PartitionConfigError("LIST partitioning requires custom_values to be specified")

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", self.table_name):
            raise PartitionConfigError(f"Invalid table name: {self.table_name}")

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", self.column):
            raise PartitionConfigError(f"Invalid column name: {self.column}")


@dataclass
class PartitionManagerConfig:
    """Global configuration for partition management."""

    default_hash_partitions: int = 4
    default_naming_pattern: str = "{table}_p{number}"
    auto_generate_enabled: bool = True
    validate_partition_keys: bool = True
    log_sql_generation: bool = True

    # Table-specific overrides
    table_configs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_table_config(self, table_name: str) -> dict[str, Any]:
        """Get configuration for a specific table."""
        return self.table_configs.get(table_name, {})


class PartitionDetector:
    """Detects partitioned tables from SQLAlchemy metadata."""

    def __init__(self, config: PartitionManagerConfig):
        self.config = config

    def detect_partitioned_tables(self, metadata: MetaData) -> dict[str, PartitionConfig]:
        """
        Detect all partitioned tables from metadata.

        Args:
            metadata: SQLAlchemy MetaData object

        Returns:
            Dictionary mapping table names to their partition configurations

        Raises:
            PartitionConfigError: If invalid partition configuration is found
        """
        partitioned_tables = {}

        for table in metadata.tables.values():
            try:
                partition_config = self._extract_partition_config(table)
                if partition_config:
                    partitioned_tables[table.name] = partition_config
                    logger.info(f"Detected partitioned table: {table.name}")
            except Exception as e:
                logger.error(f"Error processing table {table.name}: {e}")
                if self.config.validate_partition_keys:
                    raise PartitionConfigError(f"Invalid partition configuration for table {table.name}: {e}")

        return partitioned_tables

    def _extract_partition_config(self, table: Table) -> PartitionConfig | None:
        """Extract partition configuration from a table."""
        partition_by = self._get_partition_by_clause(table)
        if not partition_by:
            return None

        # Parse the partition_by clause
        strategy, column = self._parse_partition_by(partition_by)

        # Get table-specific configuration
        table_config = self.config.get_table_config(table.name)

        partition_count = table_config.get("partition_count", self.config.default_hash_partitions)

        naming_pattern = table_config.get("naming_pattern", self.config.default_naming_pattern)

        return PartitionConfig(
            table_name=table.name,
            strategy=strategy,
            column=column,
            partition_count=partition_count,
            naming_pattern=naming_pattern,
            custom_values=table_config.get("custom_values"),
            range_bounds=table_config.get("range_bounds"),
        )

    def _get_partition_by_clause(self, table: Table) -> str | None:
        """Extract the postgresql_partition_by clause from table."""
        # Check table.kwargs first (SQLAlchemy 2.0+)
        if hasattr(table, "kwargs") and "postgresql_partition_by" in table.kwargs:
            return cast(str, table.kwargs["postgresql_partition_by"])

        # Check table.info as fallback
        if "postgresql_partition_by" in table.info:
            return cast(str, table.info["postgresql_partition_by"])

        return None

    def _parse_partition_by(self, partition_by: str) -> tuple[PartitionStrategy, str]:
        """
        Parse partition_by clause to extract strategy and column.

        Examples:
            "HASH (organization_id)" -> (HASH, "organization_id")
            "RANGE (created_at)" -> (RANGE, "created_at")
            "LIST (status)" -> (LIST, "status")
        """
        # Clean up the clause
        partition_by = partition_by.strip()

        # Match pattern: STRATEGY (column_name)
        match = re.match(r"(\w+)\s*\(\s*([^)]+)\s*\)", partition_by)
        if not match:
            raise PartitionConfigError(
                f"Invalid partition_by clause: {partition_by}. " f"Expected format: 'STRATEGY (column_name)'"
            )

        strategy_str = match.group(1).upper()
        column = match.group(2).strip()

        try:
            strategy = PartitionStrategy(strategy_str)
        except ValueError:
            raise PartitionConfigError(
                f"Unsupported partition strategy: {strategy_str}. "
                f"Supported strategies: {[s.value for s in PartitionStrategy]}"
            )

        return strategy, column


class PartitionSQLGenerator:
    """Generates SQL statements for partition operations."""

    def __init__(self, config: PartitionManagerConfig):
        self.config = config

    def generate_creation_sql(self, partition_config: PartitionConfig) -> list[str]:
        """
        Generate SQL statements to create partitions.

        Args:
            partition_config: Configuration for the partitioned table

        Returns:
            List of SQL statements to create partitions

        Raises:
            PartitionSQLError: If SQL generation fails
        """
        try:
            if partition_config.strategy == PartitionStrategy.HASH:
                return self._generate_hash_partitions(partition_config)
            elif partition_config.strategy == PartitionStrategy.RANGE:
                return self._generate_range_partitions(partition_config)
            elif partition_config.strategy == PartitionStrategy.LIST:
                return self._generate_list_partitions(partition_config)
            else:
                raise PartitionSQLError(f"Unsupported partition strategy: {partition_config.strategy}")
        except Exception as e:
            raise PartitionSQLError(f"Failed to generate creation SQL for " f"{partition_config.table_name}: {e}")

    def generate_drop_sql(self, partition_config: PartitionConfig) -> list[str]:
        """Generate SQL statements to drop partitions."""
        try:
            drop_statements = []

            if partition_config.strategy in [
                PartitionStrategy.HASH,
                PartitionStrategy.RANGE,
            ]:
                for i in range(partition_config.partition_count):
                    partition_name = partition_config.naming_pattern.format(table=partition_config.table_name, number=i)
                    drop_statements.append(f"DROP TABLE IF EXISTS {partition_name}")

            elif partition_config.strategy == PartitionStrategy.LIST:
                if partition_config.custom_values:
                    for i, _ in enumerate(partition_config.custom_values):
                        partition_name = partition_config.naming_pattern.format(
                            table=partition_config.table_name, number=i
                        )
                        drop_statements.append(f"DROP TABLE IF EXISTS {partition_name}")

            if self.config.log_sql_generation:
                logger.info(f"Generated {len(drop_statements)} drop statements for " f"{partition_config.table_name}")

            return drop_statements

        except Exception as e:
            raise PartitionSQLError(f"Failed to generate drop SQL for {partition_config.table_name}: {e}")

    def _generate_hash_partitions(self, config: PartitionConfig) -> list[str]:
        """Generate HASH partition creation SQL."""
        statements = []

        for i in range(config.partition_count):
            partition_name = config.naming_pattern.format(table=config.table_name, number=i)

            sql = f"""CREATE TABLE {partition_name} PARTITION OF {config.table_name}
FOR VALUES WITH (MODULUS {config.partition_count}, REMAINDER {i})"""

            statements.append(sql)

        if self.config.log_sql_generation:
            logger.info(f"Generated {len(statements)} HASH partitions for {config.table_name}")

        return statements

    def _generate_range_partitions(self, config: PartitionConfig) -> list[str]:
        """Generate RANGE partition creation SQL."""
        if not config.range_bounds:
            raise PartitionSQLError("Range bounds not specified for RANGE partitioning")

        statements = []

        for i, (start, end) in enumerate(config.range_bounds):
            partition_name = config.naming_pattern.format(table=config.table_name, number=i)

            sql = f"""CREATE TABLE {partition_name} PARTITION OF {config.table_name}
FOR VALUES FROM ('{start}') TO ('{end}')"""

            statements.append(sql)

        if self.config.log_sql_generation:
            logger.info(f"Generated {len(statements)} RANGE partitions for {config.table_name}")

        return statements

    def _generate_list_partitions(self, config: PartitionConfig) -> list[str]:
        """Generate LIST partition creation SQL."""
        if not config.custom_values:
            raise PartitionSQLError("Custom values not specified for LIST partitioning")

        statements = []

        for i, values in enumerate(config.custom_values):
            partition_name = config.naming_pattern.format(table=config.table_name, number=i)

            # Handle single value or list of values
            if isinstance(values, (list, tuple)):  # noqa
                value_list = "', '".join(str(v) for v in values)
                sql = f"""CREATE TABLE {partition_name} PARTITION OF {config.table_name}
FOR VALUES IN ('{value_list}')"""
            else:
                sql = f"""CREATE TABLE {partition_name} PARTITION OF {config.table_name}
FOR VALUES IN ('{values}')"""

            statements.append(sql)

        if self.config.log_sql_generation:
            logger.info(f"Generated {len(statements)} LIST partitions for {config.table_name}")

        return statements


class PartitionManager:
    """Main partition management class."""

    def __init__(self, config: PartitionManagerConfig | None = None):
        self.config = config or PartitionManagerConfig()
        self.detector = PartitionDetector(self.config)
        self.sql_generator = PartitionSQLGenerator(self.config)

    def analyze_metadata(self, metadata: MetaData) -> dict[str, PartitionConfig]:
        """Analyze metadata and return partition configurations."""
        return self.detector.detect_partitioned_tables(metadata)

    def generate_migration_sql(self, metadata: MetaData) -> dict[str, dict[str, list[str]]]:
        """
        Generate complete migration SQL for all partitioned tables.

        Returns:
            Dictionary with table_name -> {'upgrade': [...], 'downgrade': [...]}
        """
        partitioned_tables = self.analyze_metadata(metadata)
        migration_sql = {}

        for table_name, config in partitioned_tables.items():
            try:
                upgrade_sql = self.sql_generator.generate_creation_sql(config)
                downgrade_sql = self.sql_generator.generate_drop_sql(config)

                migration_sql[table_name] = {
                    "upgrade": upgrade_sql,
                    "downgrade": downgrade_sql,
                }

                logger.info(f"Generated migration SQL for {table_name}")

            except Exception as e:
                logger.error(f"Failed to generate migration SQL for {table_name}: {e}")
                if self.config.validate_partition_keys:
                    raise

        return migration_sql

    def get_table_partition_info(self, table_name: str, metadata: MetaData) -> dict[str, Any] | None:
        """Get detailed partition information for a specific table."""
        partitioned_tables = self.analyze_metadata(metadata)

        if table_name not in partitioned_tables:
            return None

        config = partitioned_tables[table_name]
        upgrade_sql = self.sql_generator.generate_creation_sql(config)
        downgrade_sql = self.sql_generator.generate_drop_sql(config)

        return {
            "config": config,
            "partition_count": len(upgrade_sql),
            "upgrade_sql": upgrade_sql,
            "downgrade_sql": downgrade_sql,
            "partition_names": [
                config.naming_pattern.format(table=table_name, number=i) for i in range(config.partition_count)
            ],
        }


# Default global instance
default_partition_manager = PartitionManager()


def get_partition_manager(
    config: PartitionManagerConfig | None = None,
) -> PartitionManager:
    """Get a partition manager instance."""
    if config:
        return PartitionManager(config)
    return default_partition_manager


# Convenience functions for backward compatibility
def detect_partitioned_tables(metadata: MetaData) -> dict[str, PartitionConfig]:
    """Convenience function for detecting partitioned tables."""
    return default_partition_manager.analyze_metadata(metadata)


def generate_partition_creation_sql(table_name: str, partition_config: dict[str, Any]) -> list[str]:
    """Convenience function for generating creation SQL."""
    # Convert dict to PartitionConfig if needed
    if isinstance(partition_config, dict):
        strategy_str = partition_config.get("partition_by", "").split("(")[0].strip()
        column = partition_config.get("partition_by", "").split("(")[1].split(")")[0].strip()

        config = PartitionConfig(
            table_name=table_name,
            strategy=PartitionStrategy(strategy_str),
            column=column,
        )
    else:
        config = partition_config

    return default_partition_manager.sql_generator.generate_creation_sql(config)
