import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Skip middleware for RSC requests in development
  if (process.env.NODE_ENV === 'development' && 
      request.headers.get('rsc') === '1') {
    return NextResponse.next();
  }
  
  // Temporarily disable middleware to debug login issues
  return NextResponse.next();
}

// Configure which routes the middleware should run on
export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|logo.svg).*)',
  ],
};