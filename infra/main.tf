# TODO iam users/roles
# TODO variables for table names, lambda names

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region  = "eu-west-1"
  profile = "PersonalAWSAccount"
}

# Create a VPC
resource "aws_vpc" "private_vpc" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_dynamodb_table" "schedule_table" {
  name         = "nfl-schedule"
  billing_mode = "PROVISIONED"
  # total capacity units = 25 read + 25 write across all DDB
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

}

resource "aws_dynamodb_table" "data_table" {
  name             = "nfl-data"
  billing_mode     = "PROVISIONED"
  read_capacity    = 5
  write_capacity   = 5
  hash_key         = "id"
  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  attribute {
    name = "id"
    type = "S"
  }

}


resource "aws_s3_bucket" "site_bucket" {
  bucket = "nfl-site-8acf57f2-f8f5-4a05-ab52-4674f2837beb"

}

resource "aws_s3_bucket_acl" "site_bucket" {
  bucket = aws_s3_bucket.site_bucket.id
  acl    = "private"
}


