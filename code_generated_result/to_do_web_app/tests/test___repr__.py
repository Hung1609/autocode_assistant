import pytest
from unittest.mock import MagicMock

from backend.models import Task  # Assuming Task is defined in backend.models

def test___repr___success():
    """Test the __repr__ method returns the correct string representation."""
    task = Task(id=1, description="Buy groceries", is_complete=False)
    expected_repr = "<Task(id=1, description='Buy groceries', is_complete=False)>"
    assert repr(task) == expected_repr

def test___repr___edge_cases():
    """Test __repr__ with different values including empty strings and special characters."""
    task1 = Task(id=0, description="", is_complete=True)
    expected_repr1 = "<Task(id=0, description='', is_complete=True)>"
    assert repr(task1) == expected_repr1

    task2 = Task(id=123, description="Task with 'quotes' and special chars: !@#$", is_complete=False)
    expected_repr2 = "<Task(id=123, description='Task with \'quotes\' and special chars: !@#$', is_complete=False)>"
    assert repr(task2) == expected_repr2

    task3 = Task(id=-1, description="Negative id test", is_complete=True)
    expected_repr3 = "<Task(id=-1, description='Negative id test', is_complete=True)>"
    assert repr(task3) == expected_repr3

def test___repr___large_description():
    """Test __repr__ with a very large description."""
    long_description = "A" * 200
    task = Task(id=1, description=long_description, is_complete=False)
    expected_repr = f"<Task(id=1, description='{long_description}', is_complete=False)>"
    assert repr(task) == expected_repr