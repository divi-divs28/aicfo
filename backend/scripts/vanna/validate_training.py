"""
Validate Vanna training quality.
Tests SQL generation accuracy and training coverage.
"""
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.semantic_layer.vanna_client import get_vanna_client
from services.semantic_layer.sql_validator import sql_validator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Validation test cases
VALIDATION_TESTS = [
    {
        "question": "What is the total NPA amount?",
        "expected_tables": ["loan_accounts"],
        "expected_keywords": ["SUM", "outstanding", "DB1", "DB2", "DB3"],
        "category": "npa_analysis"
    },
    {
        "question": "Show top 10 customers by loan exposure",
        "expected_tables": ["loan_accounts"],
        "expected_keywords": ["GROUP BY", "ORDER BY", "DESC", "LIMIT", "customer"],
        "category": "customer_analysis"
    },
    {
        "question": "What is the CASA breakdown?",
        "expected_tables": ["deposit_accounts"],
        "expected_keywords": ["SBA", "CAA", "ledger_balance"],
        "category": "deposit_analysis"
    },
    {
        "question": "List deposits maturing in next 30 days",
        "expected_tables": ["deposit_accounts"],
        "expected_keywords": ["days_to_maturity", "30"],
        "category": "liquidity_analysis"
    },
    {
        "question": "Find customers with both loans and deposits",
        "expected_tables": ["loan_accounts", "deposit_accounts"],
        "expected_keywords": ["JOIN", "customer"],
        "category": "cross_sell"
    },
    {
        "question": "Show loan distribution by DPD buckets",
        "expected_tables": ["loan_accounts"],
        "expected_keywords": ["d_overdue_dpd", "CASE", "GROUP BY"],
        "category": "dpd_analysis"
    },
    {
        "question": "Show PSL vs Non-PSL breakdown",
        "expected_tables": ["loan_accounts"],
        "expected_keywords": ["psl_non_psl", "GROUP BY"],
        "category": "psl_analysis"
    },
    {
        "question": "Show NPA by branch",
        "expected_tables": ["loan_accounts"],
        "expected_keywords": ["branch", "DB1", "DB2", "DB3", "GROUP BY"],
        "category": "branch_analysis"
    },
    {
        "question": "Show loan distribution by product type",
        "expected_tables": ["loan_accounts"],
        "expected_keywords": ["d_loan_product_type", "GROUP BY"],
        "category": "product_analysis"
    },
    {
        "question": "Show dormant deposit accounts",
        "expected_tables": ["deposit_accounts"],
        "expected_keywords": ["account_status", "D"],
        "category": "account_status"
    },
]


def validate_training(execute_sql: bool = False, save_report: bool = True) -> dict:
    """
    Validate Vanna training quality.
    
    Args:
        execute_sql: Whether to execute generated SQL to verify it works
        save_report: Whether to save validation report to file
        
    Returns:
        Dictionary with validation results
    """
    logger.info("Starting training validation...")
    
    vn = get_vanna_client()
    if vn is None:
        logger.error("Vanna client not initialized")
        return {"success": False, "error": "Vanna not initialized"}
    
    # Get training status
    training_status = vn.get_training_status()
    logger.info(f"Training status: {training_status}")
    
    if not training_status.get('is_trained'):
        logger.warning("Vanna is not trained. Run training scripts first.")
        return {
            "success": False,
            "error": "Not trained",
            "training_status": training_status
        }
    
    # Connect to database if executing SQL
    if execute_sql and not vn._is_db_connected:
        logger.info("Connecting to database for SQL execution...")
        vn.connect_to_mysql_ssl()
    
    # Run validation tests
    results = []
    passed_count = 0
    failed_count = 0
    
    for i, test in enumerate(VALIDATION_TESTS, 1):
        question = test['question']
        logger.info(f"\nTest {i}/{len(VALIDATION_TESTS)}: {question}")
        
        result = {
            "question": question,
            "category": test.get('category', 'general'),
            "expected_tables": test['expected_tables'],
            "expected_keywords": test['expected_keywords'],
        }
        
        try:
            # Generate SQL
            sql = vn.generate_sql(question)
            result['generated_sql'] = sql
            
            if not sql or sql.strip() == '':
                result['status'] = 'FAIL'
                result['error'] = 'No SQL generated'
                failed_count += 1
                logger.error(f"  ✗ No SQL generated")
                results.append(result)
                continue
            
            logger.info(f"  Generated SQL: {sql[:100]}...")
            
            # Validate SQL safety
            is_valid, error = sql_validator.validate(sql)
            result['sql_valid'] = is_valid
            result['validation_error'] = error
            
            if not is_valid:
                result['status'] = 'FAIL'
                result['error'] = f'Invalid SQL: {error}'
                failed_count += 1
                logger.error(f"  ✗ Invalid SQL: {error}")
                results.append(result)
                continue
            
            # Check expected tables
            sql_upper = sql.upper()
            tables_found = all(
                t.upper() in sql_upper for t in test['expected_tables']
            )
            result['tables_found'] = tables_found
            
            # Check expected keywords
            keywords_found = sum(
                1 for k in test['expected_keywords']
                if k.upper() in sql_upper
            )
            keyword_score = keywords_found / len(test['expected_keywords'])
            result['keyword_score'] = round(keyword_score, 2)
            result['keywords_matched'] = keywords_found
            result['keywords_total'] = len(test['expected_keywords'])
            
            # Execute SQL if requested
            if execute_sql and vn._is_db_connected:
                try:
                    # Add LIMIT for safety
                    exec_sql = sql_validator.sanitize(sql)
                    df = vn.run_sql(exec_sql)
                    result['execution_success'] = True
                    result['row_count'] = len(df)
                    logger.info(f"  SQL executed successfully, {len(df)} rows returned")
                except Exception as e:
                    result['execution_success'] = False
                    result['execution_error'] = str(e)
                    logger.warning(f"  SQL execution failed: {e}")
            
            # Determine pass/fail
            passed = tables_found and keyword_score >= 0.5
            if execute_sql:
                passed = passed and result.get('execution_success', False)
            
            result['status'] = 'PASS' if passed else 'FAIL'
            
            if passed:
                passed_count += 1
                logger.info(f"  ✓ PASS (tables: {tables_found}, keywords: {keyword_score:.0%})")
            else:
                failed_count += 1
                logger.warning(f"  ✗ FAIL (tables: {tables_found}, keywords: {keyword_score:.0%})")
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            failed_count += 1
            logger.error(f"  ✗ ERROR: {e}")
        
        results.append(result)
    
    # Calculate summary
    total_tests = len(VALIDATION_TESTS)
    pass_rate = passed_count / total_tests if total_tests > 0 else 0
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total_tests,
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate": round(pass_rate, 2),
        "training_status": training_status,
        "execute_sql": execute_sql,
    }
    
    report = {
        "summary": summary,
        "results": results,
    }
    
    # Log summary
    logger.info(f"\n{'='*50}")
    logger.info(f"VALIDATION SUMMARY")
    logger.info(f"{'='*50}")
    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {passed_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Pass Rate: {pass_rate:.0%}")
    
    # Save report
    if save_report:
        report_dir = Path(__file__).parent.parent.parent / 'data' / 'vanna' / 'training_logs'
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report saved to: {report_file}")
    
    return report


def get_training_coverage() -> dict:
    """
    Get coverage statistics for training data.
    
    Returns:
        Dictionary with coverage stats
    """
    vn = get_vanna_client()
    if vn is None:
        return {"error": "Vanna not initialized"}
    
    try:
        training_data = vn.get_training_data()
        
        if not training_data:
            return {"total": 0, "coverage": {}}
        
        # Categorize training data
        coverage = {
            "ddl": [],
            "documentation": [],
            "sql": [],
        }
        
        for item in training_data:
            data_type = item.get('training_data_type', 'unknown')
            if data_type in coverage:
                coverage[data_type].append({
                    "id": item.get('id'),
                    "content_preview": str(item.get('content', ''))[:100],
                })
        
        return {
            "total": len(training_data),
            "ddl_count": len(coverage['ddl']),
            "documentation_count": len(coverage['documentation']),
            "sql_count": len(coverage['sql']),
            "coverage": coverage,
        }
        
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Vanna training")
    parser.add_argument("--execute", action="store_true", help="Execute generated SQL")
    parser.add_argument("--no-save", action="store_true", help="Don't save report")
    parser.add_argument("--coverage", action="store_true", help="Show training coverage only")
    args = parser.parse_args()
    
    if args.coverage:
        coverage = get_training_coverage()
        print(json.dumps(coverage, indent=2))
    else:
        report = validate_training(
            execute_sql=args.execute,
            save_report=not args.no_save
        )
        
        # Exit with appropriate code
        if report.get('summary', {}).get('pass_rate', 0) >= 0.7:
            sys.exit(0)
        else:
            sys.exit(1)
