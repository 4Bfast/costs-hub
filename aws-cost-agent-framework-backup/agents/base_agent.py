"""
Base Agent class following Strands Agent architecture
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, List
import logging
from datetime import datetime

@dataclass
class AgentResult:
    """Standard result format for all agents"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    report_path: Optional[str] = None
    chart_paths: Optional[List[str]] = None
    email_template_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BaseAgent(ABC):
    """
    Base class for all agents in the framework
    Implements Strands Agent pattern with:
    - Standardized execution flow
    - Error handling
    - Logging
    - Result formatting
    """
    
    def __init__(self, settings, name: str = None):
        self.settings = settings
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"agents.{self.name}")
        
    @abstractmethod
    async def _execute_core(self) -> AgentResult:
        """Core execution logic - must be implemented by subclasses"""
        pass
    
    async def execute(self) -> AgentResult:
        """
        Main execution method with error handling and timing
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting {self.name} execution...")
            
            # Validate settings
            if hasattr(self.settings, 'validate'):
                self.settings.validate()
            
            # Execute core logic
            result = await self._execute_core()
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            if result.success:
                self.logger.info(f"✅ {self.name} completed in {execution_time:.2f}s")
            else:
                self.logger.error(f"❌ {self.name} failed: {result.error}")
                
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"💥 {self.name} crashed after {execution_time:.2f}s: {e}")
            
            return AgentResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _create_success_result(self, data: Dict[str, Any], **kwargs) -> AgentResult:
        """Helper to create successful result"""
        return AgentResult(
            success=True,
            data=data,
            **kwargs
        )
    
    def _create_error_result(self, error: str, **kwargs) -> AgentResult:
        """Helper to create error result"""
        return AgentResult(
            success=False,
            error=error,
            **kwargs
        )
