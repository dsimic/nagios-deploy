"""
Example config file for nagios deploy job.
"""
import os

NAGIOS_CFG_DIR = os.path.dirname(os.path.abspath(__file__))
NAGIOS_PWD = "Password123456789"

REMOTE_NGINX_ROOT = "/etc/nginx/"
