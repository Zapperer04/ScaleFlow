provider "aws" {
  region = "us-east-1"
}

resource "aws_ecs_cluster" "mrrag_cluster" {
  name = "mrrag-platform-cluster"
}

resource "aws_ecs_task_definition" "mrrag_task" {
  family                   = "mrrag-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"

  container_definitions = jsonencode([
    {
      name      = "mrrag-api"
      image     = "mrrag-platform:latest"
      cpu       = 1024
      memory    = 2048
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
        }
      ]
    }
  ])
}
