/**
 * Products Management Scripts
 */

function deleteProduct(productId, productName) {
  const url = `/api/products/${productId}`;
  confirmDelete(url, `product "${productName}"`);
}
