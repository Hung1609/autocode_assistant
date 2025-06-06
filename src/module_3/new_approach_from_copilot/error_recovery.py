import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor by which delay increases each retry
        exceptions: Tuple of exceptions that should trigger a retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = base_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries. Last error: {e}")
                        raise
                    
                    logger.warning(f"Attempt {attempt + 1} of {func.__name__} failed: {e}. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator

class ErrorRecovery:
    """Handles error recovery strategies for the coding agent"""
    
    @staticmethod
    def handle_file_creation_error(file_path: str, error: Exception) -> bool:
        """
        Handle file creation errors with recovery strategies
        
        Args:
            file_path: Path of the file that failed to create
            error: The exception that occurred
            
        Returns:
            True if recovery was successful, False otherwise
        """
        import os
        
        logger.warning(f"File creation failed for {file_path}: {error}")
        
        try:
            # Try to create parent directories if they don't exist
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                logger.info(f"Created parent directory: {parent_dir}")
                
                # Try to create the file again
                with open(file_path, 'w', encoding='utf-8') as f:
                    pass
                logger.info(f"Successfully created file after directory fix: {file_path}")
                return True
                
        except Exception as recovery_error:
            logger.error(f"Recovery failed for {file_path}: {recovery_error}")
            return False
        
        return False
    
    @staticmethod
    def handle_llm_generation_error(file_path: str, error: Exception, fallback_content: Optional[str] = None) -> str:
        """
        Handle LLM generation errors with fallback strategies
        
        Args:
            file_path: Path of the file being generated
            error: The exception that occurred
            fallback_content: Optional fallback content to use
            
        Returns:
            Fallback content or empty string
        """
        logger.error(f"LLM generation failed for {file_path}: {error}")
        
        if fallback_content:
            logger.info(f"Using provided fallback content for {file_path}")
            return fallback_content
        
        # Generate basic fallback content based on file type
        import os
        filename = os.path.basename(file_path)
        
        if filename.endswith('.py'):
            if 'main' in filename or 'app' in filename:
                return '''# Generated fallback content
import logging

logger = logging.getLogger(__name__)

def main():
    logger.info("Application started with fallback content")
    print("This is fallback content. Please review and update.")

if __name__ == "__main__":
    main()
'''
            else:
                return '''# Generated fallback content
"""
This file was generated with fallback content due to an error.
Please review and implement the required functionality.
"""

import logging

logger = logging.getLogger(__name__)
'''
        
        elif filename.endswith('.html'):
            return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Application</title>
</head>
<body>
    <h1>Welcome to the Application</h1>
    <p>This is fallback content. Please update with proper implementation.</p>
</body>
</html>'''
        
        elif filename.endswith('.css'):
            return '''/* Generated fallback content */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    background-color: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
'''
        
        elif filename.endswith('.js'):
            return '''// Generated fallback content
console.log('Application loaded with fallback content');

// TODO: Implement required functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
});
'''
        
        else:
            return f"# Fallback content for {filename}\n# Please implement required functionality\n"

# Export commonly used decorators
llm_retry = retry_with_backoff(
    max_retries=3,
    base_delay=2.0,
    exceptions=(Exception,)  # Catch all exceptions for LLM calls
)

file_operation_retry = retry_with_backoff(
    max_retries=2,
    base_delay=0.5,
    exceptions=(OSError, IOError)  # Only retry on file operation errors
)
