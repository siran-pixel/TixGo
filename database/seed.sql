-- =======================================================
-- ShowSpot Sample Seed Data
-- =======================================================

USE `event_ticket_booking`;

-- Insert Default Admin (Password: admin@1234, bcrypt hashed)
-- Hash generated using bcrypt for 'admin@1234'
INSERT INTO `admins` (`email`, `password_hash`, `is_active`, `created_at`) 
VALUES ('admin1234@gmail.com', '$2b$12$b64XhFz9g3K16r3sY4F.t.Y3L92YlQfFm85X3uXJdC8d81k0h222K', TRUE, NOW())
ON DUPLICATE KEY UPDATE `email`=`email`;

-- Event 1: IPL Grand Final
INSERT INTO `events` (`id`, `name`, `description`, `event_type`, `banner_image`, `venue`, `city`, `event_date`, `event_time`, `total_seats`, `status`, `created_at`)
VALUES (1, 'IPL Grand Final: Chennai Super Kings vs Mumbai Indians', 'Witness high-voltage cricket action as two top giants battle for the championship trophy under blazing stadium floodlights at Chepauk.', 'Cricket', '/static/images/event_cricket.jpg', 'MA Chidambaram Stadium (Chepauk)', 'Chennai', DATE_ADD(CURDATE(), INTERVAL 2 DAY), '19:30:00', 2500, 'ACTIVE', NOW())
ON DUPLICATE KEY UPDATE `name`=`name`;

-- Event 2: Championship Cricket Match
INSERT INTO `events` (`id`, `name`, `description`, `event_type`, `banner_image`, `venue`, `city`, `event_date`, `event_time`, `total_seats`, `status`, `created_at`)
VALUES (2, 'T20 Championship Grand Final', 'Witness high-voltage cricket action as two top giants battle for the coveted championship trophy under stadium lights.', 'Cricket', '/static/images/event_cricket.jpg', 'National Stadium', 'Chennai', DATE_ADD(CURDATE(), INTERVAL 5 DAY), '19:30:00', 10000, 'ACTIVE', NOW())
ON DUPLICATE KEY UPDATE `name`=`name`;

-- Event 3: Live Music Concert
INSERT INTO `events` (`id`, `name`, `description`, `event_type`, `banner_image`, `venue`, `city`, `event_date`, `event_time`, `total_seats`, `status`, `created_at`)
VALUES (3, 'A.R. Rahman Live in Concert - Symphony of Lights', 'An enchanting evening of timeless melodies, electrifying stage performances, and iconic musical scores.', 'Concert', '/static/images/event_concert.jpg', 'YMCA Grounds', 'Bengaluru', DATE_ADD(CURDATE(), INTERVAL 8 DAY), '19:00:00', 1050, 'ACTIVE', NOW())
ON DUPLICATE KEY UPDATE `name`=`name`;

-- Event 4: Comedy Night
INSERT INTO `events` (`id`, `name`, `description`, `event_type`, `banner_image`, `venue`, `city`, `event_date`, `event_time`, `total_seats`, `status`, `created_at`)
VALUES (4, 'Standup Comedy Night with Zakir & Friends', 'Get ready for non-stop laughter, relatable jokes, and witty storytelling with India finest stand-up comedians.', 'General', '/static/images/event_comedy.jpg', 'Music Academy Hall', 'Mumbai', DATE_ADD(CURDATE(), INTERVAL 3 DAY), '20:00:00', 250, 'ACTIVE', NOW())
ON DUPLICATE KEY UPDATE `name`=`name`;
