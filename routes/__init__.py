"""
Routes Blueprint Package

This module provides Flask Blueprint registration for modular route organization.
All route modules are organized under this package for better code maintainability.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask

# Import all blueprints
from routes.main import main_bp
from routes.admin import admin_bp
from routes.alarm import alarm_bp
from routes.grid import grid_bp
from routes.export import export_bp
from routes.scheduler import scheduler_bp


def register_blueprints(app: "Flask") -> None:
    """
    Register all blueprints with the Flask application.
    
    This function safely registers all route blueprints and handles
    any import or registration errors gracefully.
    
    Args:
        app: The Flask application instance
    
    Raises:
        ImportError: If a blueprint module cannot be imported
        RuntimeError: If blueprint registration fails
    """
    try:
        # Register main business routes (dashboard, cell, monitor, scenarios)
        app.register_blueprint(main_bp)
        logging.info("✓ Main blueprint registered successfully")
        
        # Register admin routes (admin dashboard, user management, permissions)
        app.register_blueprint(admin_bp)
        logging.info("✓ Admin blueprint registered successfully")
        
        # Register alarm routes (ZTE and Nokia alarm monitoring)
        app.register_blueprint(alarm_bp)
        logging.info("✓ Alarm blueprint registered successfully")
        
        # Register grid monitoring routes (grid list, detail, export, autocomplete)
        app.register_blueprint(grid_bp)
        logging.info("✓ Grid blueprint registered successfully")
        
        # Register export routes (data export functionality)
        app.register_blueprint(export_bp)
        logging.info("✓ Export blueprint registered successfully")
        
        # Register scheduler routes (scheduled task management)
        app.register_blueprint(scheduler_bp)
        logging.info("✓ Scheduler blueprint registered successfully")
        
    except ImportError as e:
        logging.error(f"Blueprint import failed: {e}")
        raise
    except Exception as e:
        logging.error(f"Blueprint registration failed: {e}")
        raise RuntimeError(f"Failed to register blueprints: {e}")


__all__ = [
    "main_bp",
    "admin_bp",
    "alarm_bp",
    "grid_bp",
    "export_bp",
    "scheduler_bp",
    "register_blueprints",
]
