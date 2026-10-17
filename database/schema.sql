-- =======================================================
-- ShowSpot Database Schema for MySQL
-- Database: event_ticket_booking
-- =======================================================

CREATE DATABASE IF NOT EXISTS `event_ticket_booking` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `event_ticket_booking`;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `full_name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `phone` VARCHAR(20) NOT NULL,
    `is_verified` BOOLEAN DEFAULT FALSE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Admins Table
CREATE TABLE IF NOT EXISTS `admins` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_admins_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. OTP Verifications Table
CREATE TABLE IF NOT EXISTS `otp_verifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `email` VARCHAR(150) NOT NULL,
    `otp_hash` VARCHAR(255) NOT NULL,
    `purpose` ENUM('SIGNUP', 'PASSWORD_RESET') NOT NULL DEFAULT 'SIGNUP',
    `expires_at` DATETIME NOT NULL,
    `attempts` INT DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_otp_email_purpose` (`email`, `purpose`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Events Table
CREATE TABLE IF NOT EXISTS `events` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT NOT NULL,
    `event_type` ENUM('Cinema', 'Theater', 'Cricket', 'Concert', 'General') NOT NULL DEFAULT 'Cinema',
    `banner_image` VARCHAR(255) NULL,
    `venue` VARCHAR(200) NOT NULL,
    `city` VARCHAR(100) NOT NULL,
    `event_date` DATE NOT NULL,
    `event_time` TIME NOT NULL,
    `total_seats` INT NOT NULL DEFAULT 0,
    `status` ENUM('ACTIVE', 'CANCELLED', 'COMPLETED', 'DRAFT') NOT NULL DEFAULT 'ACTIVE',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_events_type_status` (`event_type`, `status`),
    INDEX `idx_events_date` (`event_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Seats Table
CREATE TABLE IF NOT EXISTS `seats` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `event_id` INT NOT NULL,
    `seat_number` VARCHAR(30) NOT NULL,
    `section` VARCHAR(50) NOT NULL DEFAULT 'Standard',
    `category` VARCHAR(50) NOT NULL DEFAULT 'Standard',
    `price` DECIMAL(10, 2) NOT NULL,
    `status` ENUM('AVAILABLE', 'LOCKED', 'BOOKED') NOT NULL DEFAULT 'AVAILABLE',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_event_seat` (`event_id`, `seat_number`),
    FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE,
    INDEX `idx_seats_event_status` (`event_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Seat Locks Table
CREATE TABLE IF NOT EXISTS `seat_locks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `seat_id` INT NOT NULL,
    `user_id` INT NULL,
    `session_token` VARCHAR(100) NOT NULL,
    `locked_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `expires_at` DATETIME NOT NULL,
    FOREIGN KEY (`seat_id`) REFERENCES `seats` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_seat_locks_expires` (`expires_at`),
    INDEX `idx_seat_locks_token` (`session_token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Bookings Table
CREATE TABLE IF NOT EXISTS `bookings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `booking_reference` VARCHAR(50) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `event_id` INT NOT NULL,
    `total_tickets` INT NOT NULL,
    `subtotal` DECIMAL(10, 2) NOT NULL,
    `convenience_fee` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `tax` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `total_amount` DECIMAL(10, 2) NOT NULL,
    `booking_status` ENUM('CONFIRMED', 'CANCELLED', 'PENDING') NOT NULL DEFAULT 'CONFIRMED',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT,
    FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE RESTRICT,
    INDEX `idx_bookings_user` (`user_id`),
    INDEX `idx_bookings_ref` (`booking_reference`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Attendees Table
CREATE TABLE IF NOT EXISTS `attendees` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `booking_id` INT NOT NULL,
    `seat_id` INT NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `age` INT NOT NULL,
    `phone` VARCHAR(20) NOT NULL,
    `city` VARCHAR(100) NOT NULL,
    FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`seat_id`) REFERENCES `seats` (`id`) ON DELETE RESTRICT,
    INDEX `idx_attendees_booking` (`booking_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Payments Table
CREATE TABLE IF NOT EXISTS `payments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `booking_id` INT NOT NULL,
    `transaction_id` VARCHAR(100) NOT NULL UNIQUE,
    `payment_method` ENUM('UPI', 'CREDIT_CARD', 'DEBIT_CARD', 'NET_BANKING') NOT NULL,
    `amount` DECIMAL(10, 2) NOT NULL,
    `payment_status` ENUM('SUCCESS', 'FAILED', 'PENDING', 'REFUNDED') NOT NULL DEFAULT 'SUCCESS',
    `paid_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`id`) ON DELETE CASCADE,
    INDEX `idx_payments_booking` (`booking_id`),
    INDEX `idx_payments_txn` (`transaction_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. Tickets Table
CREATE TABLE IF NOT EXISTS `tickets` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `booking_id` INT NOT NULL,
    `attendee_id` INT NOT NULL,
    `seat_id` INT NOT NULL,
    `ticket_number` VARCHAR(50) NOT NULL UNIQUE,
    `qr_code_path` VARCHAR(255) NOT NULL,
    `ticket_status` ENUM('ACTIVE', 'USED', 'CANCELLED') NOT NULL DEFAULT 'ACTIVE',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`attendee_id`) REFERENCES `attendees` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`seat_id`) REFERENCES `seats` (`id`) ON DELETE RESTRICT,
    INDEX `idx_tickets_booking` (`booking_id`),
    INDEX `idx_tickets_number` (`ticket_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
