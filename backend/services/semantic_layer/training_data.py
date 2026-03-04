"""
Training Data - Domain knowledge and SQL examples for Vanna.
Contains DDL schemas for auctions, bids, properties, and verified SQL queries.
"""

# =============================================================================
# DDL SCHEMAS WITH COLUMN DESCRIPTIONS
# =============================================================================

INDUSTRIES_DDL = """
-- `aicfo_db`.industries definition

CREATE TABLE "industries" (
  "id" int unsigned NOT NULL AUTO_INCREMENT,
  "industry_name" varchar(100) NOT NULL,
  "created_at" timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY ("id"),
  UNIQUE KEY `industry_name` (`industry_name`)
) 
"""

COMPANY_DDL = """
-- `aicfo_db`.company definition

CREATE TABLE "company" (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `company_name` varchar(255) NOT NULL,
  `billing_details` text,
  `zipcode` varchar(20) DEFAULT NULL,
  `city` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `country` varchar(100) DEFAULT NULL,
  `region` varchar(100) DEFAULT NULL,
  `gst_no` varchar(50) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `industry_id` int unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_company_industry` (`industry_id`),
  CONSTRAINT `fk_company_industry` FOREIGN KEY (`industry_id`) REFERENCES `industries` (`id`) ON DELETE SET NULL
)
"""

ACCOUNTS_DDL = """
CREATE TABLE IF NOT EXISTS `accounts` (
  `invoice_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `invoice_from_company` bigint unsigned NOT NULL,
  `invoice_to_company` bigint unsigned NOT NULL,
  `invoice_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
  `paid_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
  `balance_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
  `currency` varchar(10) NOT NULL,
  `invoice_date` date NOT NULL,
  `due_date` date NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status` enum('paid','partial','unpaid','overdue') DEFAULT NULL,
  PRIMARY KEY (`invoice_id`),
  KEY `fk_invoice_from_company` (`invoice_from_company`),
  KEY `fk_invoice_to_company` (`invoice_to_company`),
  CONSTRAINT `fk_invoice_from_company` FOREIGN KEY (`invoice_from_company`) REFERENCES `company` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_invoice_to_company` FOREIGN KEY (`invoice_to_company`) REFERENCES `company` (`id`) ON DELETE CASCADE
)"""

USERS_DDL = """
CREATE TABLE "users" (
  "id" int NOT NULL AUTO_INCREMENT,
  "email" varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  "name" varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  "location" varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  "profile_verified" tinyint(1) NOT NULL,
  "created_at" datetime NOT NULL,
  "password" varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  "role" varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY ("id"),
  UNIQUE KEY "email" ("email")
);
"""
DDL_STATEMENTS = [INDUSTRIES_DDL, COMPANY_DDL, ACCOUNTS_DDL,USERS_DDL]


# =============================================================================
# real estate domain DOCUMENTATION
# Provided via upload only (Business Context tab). No static data.
# =============================================================================

ASSET_DOCUMENTATION = []


# =============================================================================
# SQL TRAINING EXAMPLES (Question -> SQL pairs)f
# Provided via upload only (SQL Training tab). No static data.
# =============================================================================

SQL_TRAINING_EXAMPLES = []
