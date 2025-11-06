#!/usr/bin/env python3
"""
AWS Cost Analysis Agent Framework
"""

import asyncio
import logging
from pathlib import Path
from agents.cost_analysis_agent import CostAnalysisAgent
from config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the cost analysis framework"""
    try:
        # Load configuration
        settings = Settings()
        
        # Initialize agent
        agent = CostAnalysisAgent(settings)
        
        # Run analysis
        logger.info("🚀 Starting AWS Cost Analysis Framework...")
        result = await agent.execute()
        
        if result.success:
            logger.info(f"✅ Analysis completed successfully!")
            logger.info(f"📄 Report: {result.report_path}")
            
            # Open report
            import os
            os.system(f"open {result.report_path}")
        else:
            logger.error(f"❌ Analysis failed: {result.error}")
            
    except KeyboardInterrupt:
        logger.info("⚠️ Analysis cancelled by user")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
