import os
import imp

from fabric.api import env, sudo, run, cd, put

from deploy_common import PKG_SETUP_CMD, ADD_USER_CMD, ADD_GROUP_CMD

os, cd, put

env.use_ssh_config = True

env.NAGIOS_URL = "https://assets.nagios.com/downloads/nagioscore/" +\
    "releases/nagios-4.1.1.tar.gz"
env.NAGIOS_PLUGINS_URL = "http://nagios-plugins.org/download/" + \
    "nagios-plugins-2.1.1.tar.gz"
env.NRPE_URL = "http://downloads.sourceforge.net/project/nagios/" +\
    "nrpe-2.x/nrpe-2.15/nrpe-2.15.tar.gz"


def setup_core():
    """
    Setups up the core environment for box.
    """
    # build essentials + git
    sudo(PKG_SETUP_CMD.format("build-essential"))
    sudo(PKG_SETUP_CMD.format("libgd2-xpm-dev"))
    sudo(PKG_SETUP_CMD.format("openssl libssl-dev"))
    sudo(PKG_SETUP_CMD.format("apache2-utils"))
    sudo(PKG_SETUP_CMD.format("xinetd"))
    sudo(PKG_SETUP_CMD.format("unzip"))
    sudo(PKG_SETUP_CMD.format("apache2"))
    sudo(PKG_SETUP_CMD.format("apache2-doc apache2-utils"))
    sudo(PKG_SETUP_CMD.format("postfix"))
    sudo(PKG_SETUP_CMD.format("heirloom-mailx"))

    sudo(PKG_SETUP_CMD.format("nginx"))

    sudo(PKG_SETUP_CMD.format("php5-fpm"))
    sudo(PKG_SETUP_CMD.format("spawn-fcgi"))
    sudo(PKG_SETUP_CMD.format("fcgiwrap"))


def setup_build_nagios():
    """
    Sets up nagios
    """
    sudo(ADD_USER_CMD.format("nagios"))
    sudo(ADD_GROUP_CMD.format("nagcmd"))
    sudo("usermod -a -G nagcmd nagios")
    run("curl -L -O %s" % env.NAGIOS_URL)
    run("tar xvf nagios-*.tar.gz")
    run(
        """
        cd nagios-*;
        ./configure --with-nagios-group=nagios --with-command-group=nagcmd
        make all
        """
    )
    sudo(
        """
        cd nagios-*;
        make install
        make install-commandmode
        make install-init
        make install-config
        /usr/bin/install -c -m 644 sample-config/httpd.conf \
            /etc/apache2/sites-available/nagios.conf
        """
    )


def install_nagios_plugins():
    """
    Install some all important plugins.
    """
    run("curl -L -O %s" % env.NAGIOS_PLUGINS_URL)
    run("tar xvf nagios-plugins-*.tar.gz")
    run(
        """
        cd nagios-plugins-*
        ./configure --with-nagios-user=nagios\
            --with-nagios-group=nagios --with-openssl
        make
        """
    )
    sudo("cd nagios-plugins-*; make install")
    run("curl -L -O %s" % env.NRPE_URL)
    run("tar xvf nrpe-*.tar.gz")
    run(
        """
        cd nrpe-*
        ./configure --enable-command-args --with-nagios-user=nagios \
            --with-nagios-group=nagios --with-ssl=/usr/bin/openssl \
            --with-ssl-lib=/usr/lib/x86_64-linux-gnu
        make all
        """
    )
    sudo(
        """
        cd nrpe-*
        sudo make install
        sudo make install-xinetd
        sudo make install-daemon-config
        """
    )


def setup_nrpe():
    put(
        "{0}/xinetd.d/nrpe".format(env.CONFIG.NAGIOS_CFG_DIR),
        "/etc/xinetd.d/", use_sudo=True)
    sudo("service xinetd restart")


def setenv(cfgpath="./config_example.py"):
    env.CONFIG = imp.load_source('config', cfgpath)


def setup_nagios_cfgs():
    """
    Puts our local nagios cfg files to server.
    """
    put(
        "{0}/nagios/contacts.cfg".format(env.CONFIG.NAGIOS_CFG_DIR),
        "/usr/local/nagios/etc/objects/contacts.cfg",
        use_sudo=True
    )
    put(
        "{0}/nagios/cgi.cfg".format(env.CONFIG.NAGIOS_CFG_DIR),
        "/usr/local/nagios/etc/cgi.cfg",
        use_sudo=True
    )
    put(
        "{0}/nagios/commands.cfg".format(env.CONFIG.NAGIOS_CFG_DIR),
        "/usr/local/nagios/etc/objects/commands.cfg",
        use_sudo=True
    )
    put(
        "{0}/nagios/nagios.cfg".format(env.CONFIG.NAGIOS_CFG_DIR),
        "/usr/local/nagios/etc/nagios.cfg",
        use_sudo=True
    )
    sudo(
        """
        mkdir /usr/local/nagios/etc/servers
        chown -R nagios:nagios /usr/local/nagios/etc
        """
    )


def setup_nginx():
    """
    Configures nginx to serve nagios admin module.
    """
    put(
        "{0}/nginx/sites-available/nagios".format(env.CONFIG.NAGIOS_CFG_DIR),
        "{0}/sites-available/".format(env.CONFIG.REMOTE_NGINX_ROOT),
        use_sudo=True
    )
    put(
        "./htpasswd.pl", "/usr/local/bin/",
        use_sudo=True
    )
    sudo("chmod +x /usr/local/bin/htpasswd.pl")
    sudo(
        """
        mkdir -p /etc/nagios
        /usr/local/bin/htpasswd.pl nagiosadmin "{0}" > \
            /usr/local/nagios/etc/htpasswd.users
        """.format(env.CONFIG.NAGIOS_PWD)
    )
    sudo(
        """
        ln -sf {0}/sites-available/nagios  {0}/sites-enabled/nagios
        """.format(env.CONFIG.REMOTE_NGINX_ROOT)
    )

    sudo("service nginx restart")
    sudo("service nagios restart")


def setup_apache():
    """
    Configures apache to serve nagios admin module.
    """
    put(
        "{0}/apache2/ports.conf".format(env.CONFIG.NAGIOS_CFG_DIR),
        "/etc/apache2/",
        use_sudo=True
    )
    put(
        "{0}/apache2/000-default.conf".format(env.CONFIG.NAGIOS_CFG_DIR),
        "/etc/apache2/sites-available/",
        use_sudo=True
    )
    sudo(
        """
        a2enmod rewrite
        a2enmod cgi
        htpasswd -b -c /usr/local/nagios/etc/htpasswd.users \
            nagiosadmin {0}
        """.format(env.CONFIG.NAGIOS_PWD)
    )
    sudo(
        "ln -sf /etc/apache2/sites-available/nagios.conf" +
        " /etc/apache2/sites-enabled/")
    sudo("service nagios restart")
    sudo("service apache2 restart")
    # enable nagios to start on server boot
    sudo("ln -s /etc/init.d/nagios /etc/rcS.d/S99nagios")


def cleanup():
    """
    Delete tmp files from remote server.
    """
    run("cd; rm -rf nagios-*")


def setup_box(cfgpath="./config_example.py"):
    """
    Setups up the env for an OpenMRS box.
    """
    cleanup()
    setenv(cfgpath=cfgpath)
    setup_core()
    setup_build_nagios()
    install_nagios_plugins()
    setup_nginx()
    setup_nrpe()
    cleanup()
