#coding:utf-8
import logging

import boto
from boto.exception import S3ResponseError

from cactus.deployment.engine import BaseDeploymentEngine
from cactus.deployment.s3.auth import AWSCredentialsManager
from cactus.deployment.s3.file import S3File
from cactus.exceptions import InvalidCredentials


logger = logging.getLogger(__name__)


class S3DeploymentEngine(BaseDeploymentEngine):
    FileClass = S3File
    CredentialsManagerClass = AWSCredentialsManager

    config_bucket_name = "aws-bucket-name"
    config_bucket_website = "aws-bucket-website"

    _s3_api_endpoint = 's3.amazonaws.com'
    _s3_port = 443
    _s3_is_secure = True
    _s3_https_connection_factory = None


    def _get_buckets(self):
        """
        :returns: The list of buckets found for this account
        """
        try:
            return self.get_connection().get_all_buckets()
        except S3ResponseError as e:
            if e.error_code == u'InvalidAccessKeyId':
                logger.info("Received an Error from AWS:\n %s", e.body)
                raise InvalidCredentials()
            raise

    def _create_connection(self):
        """
        Create a new S3 Connection
        """
        aws_access_key, aws_secret_key = self.credentials_manager.get_credentials()

        return boto.connect_s3(aws_access_key.strip(), aws_secret_key.strip(),
                               host=self._s3_api_endpoint, is_secure=self._s3_is_secure, port=self._s3_port,
                               https_connection_factory=self._s3_https_connection_factory)

    def get_bucket(self):
        """
        :returns: The Bucket if found, None otherwise.
        :raises: InvalidCredentials if we can't connect to AWS
        """
        buckets = self._get_buckets()
        buckets = dict((bucket.name, bucket) for bucket in buckets)
        return buckets.get(self.bucket_name)

    def create_bucket(self):
        """
        :returns: The newly created bucket
        """
        try:
            bucket = self.get_connection().create_bucket(self.bucket_name, policy='public-read')
        except boto.exception.S3CreateError:
            logger.info(
                'Bucket with name %s already is used by someone else, '
                'please try again with another name', self.bucket_name)
            return  #TODO: These should be exceptions

        # Configure S3 to use the index.html and error.html files for indexes and 404/500s.
        bucket.configure_website(self._index_page, self._error_page)

        return bucket

    def get_website_endpoint(self):
       return self.bucket.get_website_endpoint()
