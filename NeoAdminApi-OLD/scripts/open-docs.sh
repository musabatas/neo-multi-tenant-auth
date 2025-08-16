#!/bin/bash

# Script to open API documentation in browser

echo "🚀 Opening NeoAdminApi Documentation..."
echo ""
echo "Available documentation formats:"
echo "  📚 Scalar (Recommended): http://localhost:8001/docs"
echo "  📝 Swagger UI: http://localhost:8001/swagger"
echo "  📖 ReDoc: http://localhost:8001/redoc"
echo ""

# Try to open Scalar docs (primary)
if command -v open &> /dev/null; then
    # macOS
    open http://localhost:8001/docs
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open http://localhost:8001/docs
elif command -v start &> /dev/null; then
    # Windows
    start http://localhost:8001/docs
else
    echo "⚠️  Could not automatically open browser."
    echo "Please manually navigate to: http://localhost:8001/docs"
fi

echo "✅ Documentation opened in browser!"
echo ""
echo "🏷️  New Features:"
echo "  • Nested tag groups for better organization"
echo "  • Categories with emojis for visual hierarchy"
echo "  • Grouped endpoints by functional area"
echo ""
echo "📦 Tag Groups:"
echo "  • Authentication & Authorization"
echo "  • User Management"
echo "  • Organization Management"
echo "  • Tenant Management"
echo "  • Infrastructure"
echo "  • 💳 Billing & Subscriptions (coming soon)"
echo "  • 📊 Analytics & Reports (coming soon)"
echo "  • System"
echo "  • Debug"