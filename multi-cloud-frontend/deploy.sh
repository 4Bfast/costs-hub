#!/bin/bash

# Frontend Deploy Script for CostsHub
# Usage: ./deploy.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_PROFILE="4bfast"
S3_BUCKET="costhub-frontend-4bfast"
CLOUDFRONT_DISTRIBUTION_ID="E304GP2KCWTCT0"

echo -e "${BLUE}🚀 Starting CostsHub Frontend Deploy...${NC}"
echo ""

# Step 1: Build
echo -e "${YELLOW}📦 Building frontend...${NC}"
npm run build
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Build completed successfully${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi
echo ""

# Step 2: Deploy to S3
echo -e "${YELLOW}☁️  Deploying to S3...${NC}"

# Upload assets with long cache
echo "Uploading assets with cache headers..."
AWS_PROFILE=$AWS_PROFILE aws s3 sync out/ s3://$S3_BUCKET \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "*.html"

# Upload HTML files with no cache
echo "Uploading HTML files with no-cache headers..."
AWS_PROFILE=$AWS_PROFILE aws s3 sync out/ s3://$S3_BUCKET \
    --delete \
    --cache-control "public, max-age=0, must-revalidate" \
    --include "*.html"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ S3 deployment completed${NC}"
else
    echo -e "${RED}❌ S3 deployment failed${NC}"
    exit 1
fi
echo ""

# Step 3: Invalidate CloudFront
echo -e "${YELLOW}🔄 Invalidating CloudFront cache...${NC}"
INVALIDATION_ID=$(AWS_PROFILE=$AWS_PROFILE aws cloudfront create-invalidation \
    --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ CloudFront invalidation created: $INVALIDATION_ID${NC}"
else
    echo -e "${RED}❌ CloudFront invalidation failed${NC}"
    exit 1
fi
echo ""

# Summary
echo -e "${GREEN}🎉 DEPLOY COMPLETED SUCCESSFULLY!${NC}"
echo ""
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo "• AWS Profile: $AWS_PROFILE"
echo "• S3 Bucket: $S3_BUCKET"
echo "• CloudFront: $CLOUDFRONT_DISTRIBUTION_ID"
echo "• Invalidation: $INVALIDATION_ID"
echo "• Frontend URL: https://costhub.4bfast.com.br"
echo ""
echo -e "${YELLOW}⏱️  Cache propagation: 1-2 minutes${NC}"
echo -e "${GREEN}🌐 Your frontend is now live!${NC}"
