#!/bin/bash
# Test login script
# Usage: ./scripts/test_login.sh [email] [password]

EMAIL="${1:-dev@corposostenibile.it}"
PASSWORD="${2:-Dev123?}"
BASE_URL="${BASE_URL:-http://localhost:5001}"

echo "Testing login with:"
echo "  Email: $EMAIL"
echo "  URL: $BASE_URL/api/auth/login"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

BODY=$(echo "$RESPONSE" | head -n -1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Login SUCCESS"
  echo "$BODY" | python3 -m json.tool 2>/dev/null | head -20
else
  echo "❌ Login FAILED"
  echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
fi
