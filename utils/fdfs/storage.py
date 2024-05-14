from django.core.files.storage import Storage  # 导入Storage类并对类的方法进行重写
from django.conf import settings
from fdfs_client.client import *


class FDFSStorage(Storage):
    """FDFS文件存储"""
    def __init__(self, client_conf=None, base_url=None):
        """初始化"""
        if not client_conf:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if not base_url:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def open(self, name, mode="rb"):
        '''打开文件时使用'''
        pass

    def save(self, name, content, max_length=None):
        '''保存文件时使用'''
        # name:上传的文件名
        # content:创建文件内容的File对象

        # 创建一个Fdfs_client对象
        client = Fdfs_client(self.client_conf)
        res = client.upload_by_buffer(content.read())

        # return dict
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # } if success else None

        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到fast_dfs失败')
        # 获取返回文件id
        filename = res.get('Remote file_id')

        return filename


    def exists(self, name):
        """Django判断文件名是否可用"""
        return False


    def url(self, name):
        return self.base_url + name


