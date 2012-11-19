'''
Execute calls on selinux
'''
# Import python libs
import os

# Import salt libs
import salt.utils
from salt._compat import string_types
from salt.exceptions import CommandExecutionError


def __virtual__():
    '''
    Check if the os is Linux, and then if selinux is running in permissive or
    enforcing mode.
    '''
    required_cmds = ('semanage', 'seinfo', 'setenforce', 'setsebool')

    # Iterate over all of the commands this module uses and make sure
    # each of them are available in the standard PATH to prevent breakage
    for cmd in required_cmds:
        if not salt.utils.which(cmd):
            return False
    # SELinux only makes sense on Linux *obviously*
    if __grains__['kernel'] == 'Linux' and selinux_fs_path():
        return 'selinux'
    return False


# Cache the SELinux directory to not look it up over and over
@salt.utils.memoize
def selinux_fs_path():
    '''
    Return the location of the SELinux VFS directory

    CLI Example::

        salt '*' selinux.selinux_fs_path
    '''
    # systems running systemd (e.g. Fedora 15 and newer)
    # have the selinux filesystem in a different location
    for directory in ('/sys/fs/selinux', '/selinux'):
        if os.path.isdir(directory):
            if os.path.isfile(os.path.join(directory, 'enforce')):
                return directory
    return None


def getenforce():
    '''
    Return the mode selinux is running in

    CLI Example::

        salt '*' selinux.getenforce
    '''
    enforce = os.path.join(selinux_fs_path(), 'enforce')
    try:
        with open(enforce, 'r') as _fp:
            if _fp.readline().strip() == '0':
                return 'Permissive'
            else:
                return 'Enforcing'
    except (IOError, OSError) as exc:
        msg = 'Could not read SELinux enforce file: {0}'
        raise CommandExecutionError(msg.format(str(exc)))


def setenforce(mode):
    '''
    Set the SELinux enforcing mode

    CLI Example::

        salt '*' selinux.setenforce enforcing
    '''
    if isinstance(mode, string_types):
        if mode.lower() == 'enforcing':
            mode = '1'
        elif mode.lower() == 'permissive':
            mode = '0'
        else:
            return 'Invalid mode {0}'.format(mode)
    elif isinstance(mode, int):
        if mode:
            mode = '1'
        else:
            mode = '0'
    else:
        return 'Invalid mode {0}'.format(mode)
    __salt__['cmd.run']('setenforce {0}'.format(mode))
    return getenforce()


def getsebool(boolean):
    '''
    Return the information on a specific selinux boolean

    CLI Example::

        salt '*' selinux.getsebool virt_use_usb
    '''
    return list_sebool().get(boolean, {})


def setsebool(boolean, value, persist=False):
    '''
    Set the value for a boolean

    CLI Example::

        salt '*' selinux.setsebool virt_use_usb off
    '''
    if persist:
        cmd = 'setsebool -P {0} {1}'.format(boolean, value)
    else:
        cmd = 'setsebool {0} {1}'.format(boolean, value)
    return not __salt__['cmd.retcode'](cmd)


def setsebools(pairs, persist=False):
    '''
    Set the value of multiple booleans

    CLI Example::

        salt '*' selinux.setsebools '{virt_use_usb: on, squid_use_tproxy: off}'
    '''
    if not isinstance(pairs, dict):
        return {}
    if persist:
        cmd = 'setsebool -P '
    else:
        cmd = 'setsebool '
    for boolean, value in pairs.items():
        cmd = '{0} {1}={2}'.format(cmd, boolean, value)
    return not __salt__['cmd.retcode'](cmd)


def list_sebool():
    '''
    Return a structure listing all of the selinux booleans on the system and
    what state they are in

    CLI Example::

        salt '*' selinux.list_sebool
    '''
    bdata = __salt__['cmd.run']('semanage boolean -l').splitlines()
    ret = {}
    for line in bdata[1:]:
        if not line.strip():
            continue
        comps = line.split()
        ret[comps[0]] = {
                         'State': comps[1][1:],
                         'Default': comps[3][:-1],
                         'Description': ' '.join(comps[4:])}
    return ret
