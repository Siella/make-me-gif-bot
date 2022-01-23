import datetime as dt
import io

import config
from minio import Minio
from transformer import ImageObject


class MinioClient:
    """
    Class for storage management:
    uploading (PUT) or downloading (GET) objects.
    """
    def __init__(self):
        self.client = Minio(
            config.MINIO_API_ADDRESS,
            access_key=config.ACCESS_KEY,
            secret_key=config.SECRET_ACCESS_KEY,
            secure=False,
        )

    def upload(self, user_id, obj: ImageObject, private=False):
        """
        Put an object to the storage.

        :param user_id: user ID in Telegram
        :param obj: image object
        :param private: whether to store in a private section
        """
        access = 'private' if private else 'public'
        bucket_name = '-'.join([str(user_id), access])
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)
        obj.bytes.seek(0)
        obj_name = '-'.join([
            dt.datetime.now().strftime("%m-%d-%Y-%H-%M-%S"), obj.name
        ])
        length = obj.bytes.getbuffer().nbytes
        self.client.put_object(bucket_name, obj_name, obj.bytes, length=length)

    def _download_bucket_content(self, bucket_name):
        content = []
        objects = self.client.list_objects(bucket_name)
        for obj in objects:
            try:
                obj_name = obj.object_name
                response = self.client.get_object(bucket_name, obj_name)
                stream = io.BytesIO()
                stream.name = obj_name
                stream.write(response.data)
                stream.seek(0)
                content.append(ImageObject(stream, stream.name))
            finally:
                response.close()
                response.release_conn()
        return content

    def download_generated_content(self, user_id):
        """
        Get objects for a specified user.

        :param user_id: user ID in Telegram
        :return: user's content (public & private)
        """
        content = []
        for access in ['public', 'private']:
            bucket = '-'.join([str(user_id), access])
            if self.client.bucket_exists(bucket):
                content.extend(self._download_bucket_content(bucket))
        return content

    def download_all_content(self, user_id_list=[]):
        """
        Get all users' (or specific list of users) content.

        :param user_id_list: IDs of users
        :return: users' content (only public)
        """
        all_content = []
        public_buckets = [bucket.name for bucket in self.client.list_buckets()
                          if '-public' in bucket.name]
        if user_id_list:
            public_buckets = [bucket for bucket in public_buckets
                              if bucket[:bucket.rfind('-')] in user_id_list]
        for bucket in public_buckets:
            all_content.extend(self._download_bucket_content(bucket))
        return all_content


if __name__ == '__main__':
    client = MinioClient()
    buckets = client.client.list_buckets()
    print(buckets)
