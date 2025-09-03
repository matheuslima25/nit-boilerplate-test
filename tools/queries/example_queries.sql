-- name: USERS_BY_STATUS
-- description: Busca usuários por status com paginação
-- parameters: status (string), limit (int), offset (int)
SELECT
    u.id,
    u.username,
    u.email,
    u.date_joined,
    u.is_active,
    p.phone,
    p.company
FROM auth_user u
LEFT JOIN users_profile p ON u.id = p.user_id
WHERE u.is_active = %s
ORDER BY u.date_joined DESC
LIMIT %s OFFSET %s;

-- name: USER_BY_ID
-- description: Busca usuário específico por ID
-- parameters: user_id (int)
SELECT
    u.id,
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    u.date_joined,
    u.is_active
FROM auth_user u
WHERE u.id = %s;

-- name: COUNT_ACTIVE_USERS
-- description: Conta total de usuários ativos
-- parameters: none
SELECT COUNT(*) as total_users
FROM auth_user
WHERE is_active = true;

-- name: USERS_BY_EMAIL_DOMAIN
-- description: Busca usuários por domínio de email
-- parameters: domain (string)
SELECT
    u.id,
    u.username,
    u.email,
    u.date_joined
FROM auth_user u
WHERE u.email LIKE CONCAT('%@', %s)
ORDER BY u.date_joined DESC;
