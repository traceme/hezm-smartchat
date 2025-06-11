# SmartChat AWS Infrastructure Outputs

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.smartchat_vpc.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public_subnets[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private_subnets[*].id
}

output "security_group_alb_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb_sg.id
}

output "security_group_app_id" {
  description = "ID of the application security group"
  value       = aws_security_group.app_sg.id
}

output "security_group_db_id" {
  description = "ID of the database security group"
  value       = aws_security_group.db_sg.id
}

output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.smartchat_alb.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.smartchat_alb.zone_id
}

output "alb_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.smartchat_alb.arn
}

output "backend_target_group_arn" {
  description = "ARN of the backend target group"
  value       = aws_lb_target_group.backend_tg.arn
}

output "frontend_target_group_arn" {
  description = "ARN of the frontend target group"
  value       = aws_lb_target_group.frontend_tg.arn
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.smartchat_postgres.endpoint
}

output "database_port" {
  description = "RDS instance port"
  value       = aws_db_instance.smartchat_postgres.port
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.smartchat_postgres.db_name
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_replication_group.smartchat_redis.primary_endpoint_address
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_replication_group.smartchat_redis.port
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.smartchat_files.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.smartchat_files.arn
}

output "launch_template_id" {
  description = "ID of the launch template"
  value       = aws_launch_template.smartchat_lt.id
}

output "autoscaling_group_name" {
  description = "Name of the autoscaling group"
  value       = aws_autoscaling_group.smartchat_asg.name
}

output "autoscaling_group_arn" {
  description = "ARN of the autoscaling group"
  value       = aws_autoscaling_group.smartchat_asg.arn
}

output "ssl_certificate_arn" {
  description = "ARN of the SSL certificate"
  value       = aws_acm_certificate.smartchat_cert.arn
}

output "iam_role_arn" {
  description = "ARN of the EC2 IAM role"
  value       = aws_iam_role.ec2_role.arn
}

output "iam_instance_profile_name" {
  description = "Name of the IAM instance profile"
  value       = aws_iam_instance_profile.ec2_profile.name
}

# Connection strings for applications
output "database_url" {
  description = "Database connection URL"
  value       = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.smartchat_postgres.endpoint}:${aws_db_instance.smartchat_postgres.port}/${var.db_name}"
  sensitive   = true
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://:${var.redis_auth_token}@${aws_elasticache_replication_group.smartchat_redis.primary_endpoint_address}:${aws_elasticache_replication_group.smartchat_redis.port}"
  sensitive   = true
}

# DNS Configuration helper
output "dns_configuration" {
  description = "DNS configuration instructions"
  value = {
    domain      = var.domain_name
    record_type = "CNAME"
    record_name = var.domain_name
    record_value = aws_lb.smartchat_alb.dns_name
    ttl         = 300
  }
}

# Summary information
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    environment        = var.environment
    region            = var.aws_region
    vpc_cidr          = var.vpc_cidr
    public_subnets    = length(aws_subnet.public_subnets)
    private_subnets   = length(aws_subnet.private_subnets)
    instance_type     = var.instance_type
    min_instances     = var.asg_min_size
    max_instances     = var.asg_max_size
    desired_instances = var.asg_desired_capacity
    db_instance_class = var.db_instance_class
    redis_node_type   = var.redis_node_type
    domain_name       = var.domain_name
    load_balancer_dns = aws_lb.smartchat_alb.dns_name
  }
} 