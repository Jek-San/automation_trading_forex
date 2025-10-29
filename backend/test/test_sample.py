import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.strategies.swing_point_fib.fib_backtest_service import FibBacktestService

FibBacktestService().run_all()
print("Done")