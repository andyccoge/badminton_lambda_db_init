import json
import boto3
import pymysql
import os
import requests

def get_secret(secret_name, region_name="ap-northeast-1"):
    client = boto3.client('secretsmanager', region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

def lambda_handler(event, context):
    db_name = 'badminton_db_1'
    db_host = os.environ.get('DB_HOST')
    db_port = int(os.environ.get('DB_PORT'))

    # 從 AWS Secrets Manager 取得 DB 資訊
    secret_name = os.environ.get("DB_SECRET_NAME", "")
    secret = get_secret(secret_name)
    db_user = secret["username"]
    db_password = secret["password"]
    # return {"statusCode": 210, "body": f"test::{db_user}::{db_password}"}

    # 建立資料庫
    try:
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        # return {"statusCode": 200, "body": "Database created successfully"}
    except Exception as e:
        return {"statusCode": 500, "body": f"Database creation failed: {str(e)}"}

    # 建立連線
    try:
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            db=db_name
        )
        # return {"statusCode": 200, "body": "MySQL connection successful"}
    except Exception as e:
        return {"statusCode": 500, "body": f"Database connection error: {str(e)}"}

    # 建立表格
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS `{db_name}`.`users` (
                    `id` INT NOT NULL AUTO_INCREMENT,
                    `name` VARCHAR(255) NOT NULL COMMENT '姓名',
                    `name_line` VARCHAR(255) NOT NULL COMMENT '姓名(LINE)',
                    `name_nick` VARCHAR(255) NOT NULL COMMENT '暱稱',
                    `email` VARCHAR(255) NOT NULL COMMENT '信箱',
                    `cellphone` VARCHAR(255) NOT NULL COMMENT '手機',
                    `gender` TINYINT(1) NOT NULL COMMENT '性別(1.男 2.女)',
                    `level` INT(11) NOT NULL COMMENT '等級(目前狀態)',
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (`id`),
                    UNIQUE KEY `name_email_cellphone_UNIQUE` (`name`, `email`, `cellphone`)
                ) COMMENT = '人員(球員)';
            """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS `{db_name}`.`play_date` (
                    `id` INT NOT NULL AUTO_INCREMENT,
                    `datetime` TIMESTAMP NOT NULL COMMENT '開場日期&時間',
                    `datetime_e` TIMESTAMP NOT NULL COMMENT '開場日期&時間(結束)',
                    `location` VARCHAR(255) DEFAULT NULL COMMENT '地點',
                    `note` VARCHAR(255) DEFAULT NULL COMMENT '備註',
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (`id`)
                ) COMMENT = '打球日，紀錄開團日期&時間、地點、備註(ex:費用、等級...)';
            """)

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS `{db_name}`.`courts` (
                    `id` INT NOT NULL AUTO_INCREMENT,
                    `play_date_id` INT NOT NULL COMMENT '場地對應打球日id',
                    `code` VARCHAR(255) DEFAULT NULL COMMENT '場地代號',
                    `type` TINYINT(1) NOT NULL COMMENT '類型(1.比賽 2.預備)',
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (`id`),
                    CONSTRAINT `fk_courts_play_date`
                        FOREIGN KEY (`play_date_id`)
                        REFERENCES `{db_name}`.`play_date` (`id`)
                        ON DELETE NO ACTION
                        ON UPDATE NO ACTION
                ) COMMENT = '打球日場地設定';
            """)

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS `{db_name}`.`reservations` (
                    `id` INT NOT NULL AUTO_INCREMENT,
                    `user_id` INT NOT NULL COMMENT '對應人員id',
                    `play_date_id` INT NOT NULL COMMENT '對應打球日id',
                    `show_up` TINYINT(1) DEFAULT 0 COMMENT '報到(0.未到 1.到)',
                    `leave` TINYINT(1) DEFAULT 0 COMMENT '離場(0.未離開 1.離開)',
                    `paid` TINYINT(1) DEFAULT 0 COMMENT '付款狀態(0.未付款 1.已付)',
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (`id`),
                    INDEX `fk_reservations_users_idx` (`user_id` ASC) VISIBLE,
                    INDEX `fk_reservations_play_date_idx` (`play_date_id` ASC) VISIBLE,
                    CONSTRAINT `fk_reservations_users`
                        FOREIGN KEY (`user_id`)
                        REFERENCES `{db_name}`.`users` (`id`)
                        ON DELETE NO ACTION
                        ON UPDATE NO ACTION,
                    CONSTRAINT `fk_reservations_play_date`
                        FOREIGN KEY (`play_date_id`)
                        REFERENCES `{db_name}`.`play_date` (`id`)
                        ON DELETE NO ACTION
                        ON UPDATE NO ACTION,
                    UNIQUE KEY `play_date_id_user_id_UNIQUE` (`play_date_id`, `user_id`)
                ) COMMENT = '報名紀錄，某人報名了某天打球的紀錄';
            """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS `{db_name}`.`matchs` (
                    `id` INT NOT NULL AUTO_INCREMENT,
                    `user_id_1` INT NOT NULL COMMENT '球員1(對應人員id)',
                    `user_id_2` INT NOT NULL COMMENT '球員2(對應人員id)',
                    `user_id_3` INT NOT NULL COMMENT '球員3(對應人員id)',
                    `user_id_4` INT NOT NULL COMMENT '球員4(對應人員id)',
                    `play_date_id` INT NOT NULL COMMENT '對應打球日id',
                    `court_id` INT NOT NULL COMMENT '對應場地id',
                    `point_12` INT DEFAULT 0 COMMENT '第一組分數',
                    `point_34` INT DEFAULT 0 COMMENT '第二組分數',
                    `duration` INT DEFAULT 0 COMMENT '比賽費時(秒)',
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (`id`),
                    INDEX `fk_matchs_users_idx_1` (`user_id_1` ASC) VISIBLE,
                    INDEX `fk_matchs_users_idx_2` (`user_id_2` ASC) VISIBLE,
                    INDEX `fk_matchs_users_idx_3` (`user_id_3` ASC) VISIBLE,
                    INDEX `fk_matchs_users_idx_4` (`user_id_4` ASC) VISIBLE,
                    INDEX `fk_matchs_play_date_idx` (`play_date_id` ASC) VISIBLE,
                    CONSTRAINT `fk_matchs_users_1`
                        FOREIGN KEY (`user_id_1`)
                        REFERENCES `{db_name}`.`users` (`id`)
                        ON DELETE NO ACTION
                        ON UPDATE NO ACTION,
                    CONSTRAINT `fk_matchs_users_2`
                        FOREIGN KEY (`user_id_2`)
                        REFERENCES `{db_name}`.`users` (`id`)
                        ON DELETE NO ACTION
                        ON UPDATE NO ACTION,
                    CONSTRAINT `fk_matchs_users_3`
                        FOREIGN KEY (`user_id_3`)
                        REFERENCES `{db_name}`.`users` (`id`)
                        ON DELETE NO ACTION
                        ON UPDATE NO ACTION,
                    CONSTRAINT `fk_matchs_users_4`
                        FOREIGN KEY (`user_id_4`)
                        REFERENCES `{db_name}`.`users` (`id`)
                        ON DELETE NO ACTION
                        ON UPDATE NO ACTION,
                    CONSTRAINT `fk_matchs_play_date`
                        FOREIGN KEY (`play_date_id`)
                        REFERENCES `{db_name}`.`play_date` (`id`)
                        ON DELETE NO ACTION
                        ON UPDATE NO ACTION,
                    CONSTRAINT `fk_matchs_courts`
                        FOREIGN KEY (`court_id`)
                        REFERENCES `{db_name}`.`courts` (`id`)
                        ON DELETE NO ACTION
                        ON UPDATE NO ACTION
                ) COMMENT = '比賽紀錄，記錄所有比賽的紀錄，包含4個球員、場地、日期、分數';
            """)
        return {"statusCode": 200, "body": "Tables created successfully"}
    except Exception as e:
        return {"statusCode": 500, "body": f"Tables creation error: {str(e)}"}
