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
  acl    = "public-read"
}


resource "aws_s3_bucket_website_configuration" "site_bucket" {
  bucket = aws_s3_bucket.site_bucket.bucket

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "404.html"
  }

}

resource "aws_s3_bucket_policy" "site_bucket" {
  bucket = aws_s3_bucket.site_bucket.id
  policy = data.aws_iam_policy_document.site_bucket.json
}

data "aws_iam_policy_document" "site_bucket" {
  statement {
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "${aws_s3_bucket.site_bucket.arn}/*"
    ]
  }
}
#
#resource "aws_acm_certificate" "site_bucket" {
#  provider                  = aws.acm_provider
#  domain_name               = var.domain_name
#  subject_alternative_names = ["*.${var.domain_name}"]
#  validation_method         = "EMAIL"
#  #validation_method = "DNS"
#
#  tags = var.common_tags
#
#  lifecycle {
#    create_before_destroy = true
#  }
#}
#
## Uncomment the validation_record_fqdns line if you do DNS validation instead of Email.
#resource "aws_acm_certificate_validation" "cert_validation" {
#  provider        = aws.acm_provider
#  certificate_arn = aws_acm_certificate.ssl_certificate.arn
#  #validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
#}