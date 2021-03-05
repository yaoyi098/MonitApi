"""
@copyright

"""

import requests
import json

from .conf import BASE_URL, DEBUG

MONIT_API_TYPE = {
    'INDEX': '/index.csp',
    'LOGIN': '/z_security_check',
    'LOGOUT': '/login/logout.csp',
    'HOST_LIST': '/status/hosts/list',
    'MAP_NAME_HOST': '/map/name/host',
    'HOST_SUMMARY': '/status/hosts/summary',
    'HOST_GET': '/status/hosts/summary',
    'HOST_DETAIL_GET': '/status/hosts/get'
}


def percent2span(percent):
    if percent <= 80:
        return '<span style="background-color: #00ff00;">%5.1f%s</span>' % (percent, r'%')
    elif percent <= 85:
        return '<span style="background-color: orange;">%5.1f%s</span>' % (percent, r'%')
    else:
        return '<span style="background-color: #ff0000;">%5.1f%s</span>' % (percent, r'%')


def filesystem2html(filesystem_list, name_str):

    t_dict = {}
    for i in filesystem_list:
        t_name = i.get('name')
        ls_statistics = i.get('statistics')
        for y in ls_statistics:
            if y.get('type') == 18:
                t_dict[t_name] = y.get('value')

    t_str = '<p><span style="font-size: 20px;">%s 文件系统信息</span></p>' % name_str
    t_str += '<table border="1" style="width: 100%;">'
    t_str += '<tr><th>Name</th><th>Space Usage Percent</th></tr>'
    for i in t_dict:
        t_str += '<tr><td>&nbsp;&nbsp;%s</td><td  align="center">%s</td></tr>' % (
            i, percent2span(t_dict[i]))

    t_str += '</table>'
    return t_str


class MonitHost():
    """
    docstring
    """

    def __init__(self, host_dict: dict):

        self.name = host_dict.get('hostname')
        self.id = host_dict.get('id')

        # led: 0=red 1=orange 2=green 3=grey
        self.led = host_dict.get('led', 3)
        self.status = host_dict.get('status', 'None')
        self.events = host_dict.get('events', 0)
        self.cpu = host_dict.get('cpu', 0.0)
        self.mem = host_dict.get('mem', 0.0)
        self.heartbeat = host_dict.get('heartbeat', 0)

    def get_led_str(self):
        """
        docstring
        """
        if self.led == 2:
            return 'OK'
        elif self.led == 1:
            return 'Warning'
        elif self.led == 3:
            return 'Inactive'
        else:
            return 'Error'

    def get_led_html(self):

        if self.led == 2:
            return '<span style="background-color: #00ff00;">OK</span>'
        elif self.led == 1:
            return '<span style="background-color: #ff6700;">Warning</span>'
        else:
            return '<span style="background-color: #ff0000;">Error</span>'

    def get_status_table(self):
        '''
        return <tr><td></td></tr>
        '''
        return '<tr><td align="center">{:^s}</td><td>&nbsp;&nbsp;{:<20s}</td><td>&nbsp;&nbsp;{:<s}</td></tr>'.format(
            self.get_led_html(), self.name, self.status)


class MonitApi():

    def __init__(self, z_u='', z_p='', base_url=BASE_URL):
        self.z_username = z_u
        self.z_password = z_p
        self.__base_url = base_url

        self.__session = requests.session()
        self.__login()

        self.list_host = []
        self.__host_init()

    def log_out(self):
        self.list_host.clear()
        self._get(MONIT_API_TYPE['LOGOUT'])
        self.__session.close()

    def _get(self, url, data=None):
        r = self.__session.get(self.__make_url(url))
        self.__debug_req(r)
        return r

    def _post(self, url, data=None):
        r = self.__session.post(self.__make_url(url), data)
        self.__debug_req(r)
        return r

    def __make_url(self, shortUrl):
        if shortUrl[0] == '/':
            return self.__base_url + shortUrl
        else:
            return self.__base_url + '/' + shortUrl

    def __get_hostnamemap(self):
        r = self._get(MONIT_API_TYPE['MAP_NAME_HOST'])
        dict_temp = json.loads(r.content)
        return dict_temp['map']['name']['host']

    def __debug_req(self, r):
        if DEBUG:
            print(r.url, r)

    def __login(self):
        if DEBUG:
            print('MonitApi instance created.')
        self._get(MONIT_API_TYPE['INDEX'])

        login_data = {
            "z_username": self.z_username,
            "z_password": self.z_password,
            "z_csrf_protection": "off"
        }
        r = self._post(MONIT_API_TYPE['LOGIN'], login_data)
        if 'Invalid username' in r.text:
            raise RuntimeError('Invalid username and/or password!')

    def __host_init(self):
        """
        docstring
        """
        dict_name_host = self.__get_hostnamemap()
        for i in sorted(dict_name_host):
            self.list_host.append(
                self.__get_hostinstance_from_id(dict_name_host[i]))

    def __get_hostinstance_from_id(self, id):
        p_data = {
            'hostid': id
        }
        r = self._post(MONIT_API_TYPE['HOST_LIST'], p_data)
        t_dict = json.loads(r.content)
        t_dict = t_dict.get('records')[0]
        t_host = MonitHost(t_dict)
        return t_host

    def _get_hostservices_from_id(self, id):
        p_data = {
            'hostid': id
        }
        r = self._post(('/status/hosts/get?id=%s' % str(id)))
        t_dict = json.loads(r.content)
        t_list = t_dict.get('records').get('host').get('services')
        return t_list

    def _get_filesystem_info(self, id):
        """
        return list
        """
        r_list = []
        t_list = self._get_hostservices_from_id(id)
        for i in t_list:
            if i.get('typeid') == 0:
                r_list.append(i)
        return r_list

    '''
    User methode
    '''

    def get_host_summary_html(self):
        send_str = """<br>
        <h1 style="font-size: 20px;"><strong>EM 系统状态：</strong></h1>
        <table border="1" style="width: 100%;">"""

        for i in self.list_host:
            send_str += i.get_status_table()

        send_str += '</table>\n'
        return send_str

    def get_ALL_filesystem_html(self):
        r_str = ""

        for i in self.list_host:
            t_list = self._get_filesystem_info(i.id)
            if t_list:
                r_str += filesystem2html(t_list, i.name)
        return r_str
