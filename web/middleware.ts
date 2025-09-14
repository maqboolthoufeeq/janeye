import { NextRequest, NextResponse } from "next/server";
import {
  isProtectedRoute,
  isUnauthenticatedOnlyRoute,
  isOrgCreationRoute,
  AUTH_ROUTES,
  DASHBOARD_ROUTES,
} from "@/routes";

// Cookie configuration matching auth.ts
const AUTH_COOKIE_CONFIG = {
  TOKEN_NAME: "access_token",
  REFRESH_TOKEN_NAME: "refresh_token",
  USER_ID_NAME: "user_id",
  ORG_ID_NAME: "org_id",
} as const;

// Helper to check if user has valid auth cookies
function hasAuthCookies(request: NextRequest): boolean {
  const accessToken = request.cookies.get(AUTH_COOKIE_CONFIG.TOKEN_NAME);
  const refreshToken = request.cookies.get(
    AUTH_COOKIE_CONFIG.REFRESH_TOKEN_NAME
  );

  return !!(accessToken?.value && refreshToken?.value);
}

// Helper to check if user has an organization
function hasOrganization(request: NextRequest): boolean {
  const orgId = request.cookies.get(AUTH_COOKIE_CONFIG.ORG_ID_NAME);
  return !!orgId?.value;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isAuthenticated = hasAuthCookies(request);
  const hasOrg = hasOrganization(request);

  console.log(
    `Middleware: ${pathname}, authenticated: ${isAuthenticated}, hasOrg: ${hasOrg}`
  );

  // Check if the current route requires authentication
  if (isProtectedRoute(pathname)) {
    if (!isAuthenticated) {
      console.log(`Redirecting unauthenticated user from ${pathname} to login`);
      const loginUrl = new URL(AUTH_ROUTES.LOGIN, request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }

    // If authenticated but no organization and not on org creation route, redirect to activity setup
    if (!hasOrg && !isOrgCreationRoute(pathname)) {
      console.log(
        `Redirecting user without organization from ${pathname} to activity setup`
      );
      return NextResponse.redirect(
        new URL(AUTH_ROUTES.SIGNUP_ACTIVITY, request.url)
      );
    }
  }

  // Check if the current route should only be accessible when NOT logged in
  if (isUnauthenticatedOnlyRoute(pathname)) {
    if (isAuthenticated) {
      console.log(
        `Redirecting authenticated user from ${pathname} to dashboard`
      );
      return NextResponse.redirect(new URL(DASHBOARD_ROUTES.ROOT, request.url));
    }
  }

  // If user is on organization creation route but already has an organization, redirect to dashboard
  if (isOrgCreationRoute(pathname) && isAuthenticated && hasOrg) {
    console.log(
      `Redirecting user with organization from ${pathname} to dashboard`
    );
    return NextResponse.redirect(new URL(DASHBOARD_ROUTES.ROOT, request.url));
  }

  // Handle redirect parameter after successful login
  if (pathname === DASHBOARD_ROUTES.ROOT && isAuthenticated) {
    const redirectParam = request.nextUrl.searchParams.get("redirect");
    if (redirectParam && isProtectedRoute(redirectParam)) {
      console.log(`Redirecting to requested page: ${redirectParam}`);
      return NextResponse.redirect(new URL(redirectParam, request.url));
    }
  }

  return NextResponse.next();
}

// Configure which paths the middleware should run on
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (images, icons, etc.)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|public|icons|img|audio).*)",
  ],
};
