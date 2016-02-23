import os

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
    # put("./xinetd/nrpe", "/etc/xinetd.d", use_sudo=True)
    # sudo("service xinetd restart")


def cleanup():
    """
    Delete tmp files from remote server.
    """
    run("cd; rm -rf nagios-*")


def setup_box(
):
    """
    Setups up the env for an OpenMRS box.
    """
    setup_core()
    setup_build_nagios()
