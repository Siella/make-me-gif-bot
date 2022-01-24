import datetime as dt
import io
from collections import defaultdict
from unittest.mock import patch

from source.storage import MinioClient


class FakeObj:
    def __init__(self, name: str, data: str = 'test'):
        self.name = name
        self.bytes = io.BytesIO(str.encode(data))


class FakeResponse:
    def __init__(self, name: str, bytes_: io.BytesIO):
        self.data = bytes_.getvalue()
        self.object_name = name

    def close(self):
        pass

    def release_conn(self):
        pass


class FakeBucket:
    def __init__(self, name: str):
        self.name = name


class FakeClient:
    """
    Fake Minio client.
    """
    buckets = dict()  # storage
    bucket_dict = dict()

    def bucket_exists(self, bucket_name: str):
        """Checks bucket existence."""
        return bucket_name in list(map(lambda x: x.name, self.buckets))

    def make_bucket(self, bucket_name: str):
        """Creates new bucket if not exists."""
        if not self.bucket_exists(bucket_name):
            self.bucket_dict[bucket_name] = FakeBucket(bucket_name)
            self.buckets[self.bucket_dict[bucket_name]] = defaultdict(None)

    def list_buckets(self):
        """Returns buckets."""
        return self.buckets

    def put_object(self,
                   bucket_name: str,
                   obj_name: str,
                   obj_bytes: bytes,
                   *args, **kwargs):
        """Puts an object to the bucket."""
        if self.bucket_exists(bucket_name):
            resp = FakeResponse(obj_name, obj_bytes)
            self.buckets[self.bucket_dict[bucket_name]][obj_name] = resp

    def get_object(self, bucket_name: str, obj_name: str):
        """Gets an object from the bucket."""
        if self.bucket_exists(bucket_name):
            return self.buckets[self.bucket_dict[bucket_name]][obj_name]
        return

    def list_objects(self, bucket_name):
        print(bucket_name)
        if self.bucket_exists(bucket_name):
            print(self.buckets[self.bucket_dict[bucket_name]].values())
            return self.buckets[self.bucket_dict[bucket_name]].values()
        return []


@patch('source.storage.Minio', return_value=FakeClient())
def test_minio_client(mock):
    client = MinioClient()

    client.upload(user_id=1, obj=FakeObj('test_1'), private=True)
    client.upload(user_id=2, obj=FakeObj('test_2'), private=True)
    client.upload(user_id=2, obj=FakeObj('test_3'), private=False)
    assert len(client.client.buckets) == 3

    content = client.download_all_content()
    date = dt.datetime.now().date().strftime("%m-%d-%Y")
    assert len(content) == 1
    assert 'test_3' in content[0].name
    assert date in content[0].name

    content = client.download_all_content(['1', '2'])
    assert len(content) == 1

    content = client.download_generated_content(2)
    assert len(content) == 2
