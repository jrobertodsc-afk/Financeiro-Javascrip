class BaseTab:
    """
    Base class for all tabs to break the God Object anti-pattern.
    It takes the main application context (app) and delegates any
    unknown attribute lookups to the main app. This allows a smooth
    transition from Mixins to independent components.
    """
    def __init__(self, app):
        self.app = app
        
    def __getattr__(self, name):
        # Delegate to the main app for shared state, methods, etc.
        # This keeps compatibility with code that used `self.rodando` or `self._log`
        return getattr(self.app, name)
