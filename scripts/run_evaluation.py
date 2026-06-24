"""
Run comprehensive evaluation on the system.
Usage: python -m scripts.run_evaluation
"""

import logging
from evaluation.metrics import EvaluationMetrics
from evaluation.test_cases import TestSetGenerator
from evaluation.adversarial_tests import AdversarialTestSuite

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("="*60)
    logger.info("SYSTEM EVALUATION")
    logger.info("="*60)
    
    # Initialize
    metrics = EvaluationMetrics()
    
    # Run golden dataset evaluation
    logger.info("\n1. Golden Dataset Evaluation")
    logger.info("-"*60)
    test_cases = TestSetGenerator.get_golden_dataset()
    logger.info(f"Test cases: {len(test_cases)}")
    
    # Run adversarial tests
    logger.info("\n2. Adversarial Testing")
    logger.info("-"*60)
    adversarial = AdversarialTestSuite.get_test_cases()
    logger.info(f"Adversarial cases: {len(adversarial)}")
    
    # TODO: Actually run tests with query system
    # For now, just show what would be evaluated
    
    logger.info("\n" + "="*60)
    logger.info("Evaluation framework ready!")
    logger.info("="*60)


if __name__ == "__main__":
    main()