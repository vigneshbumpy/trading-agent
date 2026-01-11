# Dashboard modules
# Re-export from views for backward compatibility

from dashboard.views import home
from dashboard.views import portfolio
from dashboard.views import trade_history
from dashboard.views import settings
from dashboard.views import documentation

# Use enhanced analysis page with graceful error handling and TradingView
from dashboard.modules import analysis
