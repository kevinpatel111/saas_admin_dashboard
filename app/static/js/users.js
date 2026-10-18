/**
 * Users Management Scripts
 */

function deleteUser(userId, userName) {
  const url = `/api/users/${userId}`;
  confirmDelete(url, `user "${userName}"`);
}
