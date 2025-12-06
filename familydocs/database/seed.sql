-- ============================================================================
-- FamilyDocs Intelligence Hub - Seed Data
-- ============================================================================
-- Test data for development
-- ============================================================================

-- Wait for schema to be created
\c familydocs;

-- Create root workspace
INSERT INTO boards (id, name, type, description, workspace_id, icon, color, canvas_x, canvas_y, created_by)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'FamilyDocs', 'folder', 'Root workspace for family documents', 'default', '🏠', '#8b5cf6', 0, 0, 'system')
ON CONFLICT (id) DO NOTHING;

-- Create Family board
INSERT INTO boards (id, name, type, parent_id, description, workspace_id, icon, color, canvas_x, canvas_y)
VALUES
    ('00000000-0000-0000-0000-000000000002', 'Familie', 'folder', '00000000-0000-0000-0000-000000000001', 'Familienbezogene Dokumente', 'default', '👨‍👩‍👧‍👦', '#ec4899', 100, 100)
ON CONFLICT (id) DO NOTHING;

-- Create School board
INSERT INTO boards (id, name, type, parent_id, description, workspace_id, icon, color, canvas_x, canvas_y)
VALUES
    ('00000000-0000-0000-0000-000000000003', 'Schule', 'board', '00000000-0000-0000-0000-000000000002', 'Schulunterlagen für Kinder', 'default', '🎓', '#3b82f6', 200, 200)
ON CONFLICT (id) DO NOTHING;

-- Create Health board
INSERT INTO boards (id, name, type, parent_id, description, workspace_id, icon, color, canvas_x, canvas_y)
VALUES
    ('00000000-0000-0000-0000-000000000004', 'Gesundheit', 'board', '00000000-0000-0000-0000-000000000002', 'Arztbriefe, Rezepte, etc.', 'default', '🏥', '#10b981', 400, 200)
ON CONFLICT (id) DO NOTHING;

-- Create Finance board
INSERT INTO boards (id, name, type, parent_id, description, workspace_id, icon, color, canvas_x, canvas_y)
VALUES
    ('00000000-0000-0000-0000-000000000005', 'Finanzen', 'board', '00000000-0000-0000-0000-000000000001', 'Bankbriefe, Rechnungen, Verträge', 'default', '💰', '#f59e0b', 600, 100)
ON CONFLICT (id) DO NOTHING;

-- Create links between boards
INSERT INTO board_links (board_id_from, board_id_to, link_type, reason)
VALUES
    ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000004', 'related', 'Schulkrankheit benötigt Attest')
ON CONFLICT DO NOTHING;

-- Create a test chat session
INSERT INTO chat_sessions (id, session_name, board_id, is_persistent, user_id)
VALUES
    ('00000000-0000-0000-0000-000000000101', 'Erste Chat Session', '00000000-0000-0000-0000-000000000003', true, 'default_user')
ON CONFLICT (id) DO NOTHING;

-- Create test chat messages
INSERT INTO chat_messages (session_id, role, content, agent_used, model_used)
VALUES
    ('00000000-0000-0000-0000-000000000101', 'user', 'Hallo! Kannst du mir bei meinen Schulunterlagen helfen?', null, null),
    ('00000000-0000-0000-0000-000000000101', 'assistant', 'Natürlich! Ich kann dir dabei helfen, deine Schulunterlagen zu organisieren. Was möchtest du tun?', 'chat_agent', 'qwen2.5-32b')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Success message
-- ============================================================================

SELECT 'Seed data inserted successfully!' AS status;
