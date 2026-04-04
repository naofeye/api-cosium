import { NextResponse, type NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  // httpOnly cookie readable server-side, or fallback to auth flag
  const token = request.cookies.get("optiflow_token")?.value || request.cookies.get("optiflow_authenticated")?.value;
  const pathname = request.nextUrl.pathname;
  const isLoginPage = pathname === "/login";
  const isPublicPage =
    isLoginPage ||
    pathname.startsWith("/onboarding") ||
    pathname === "/getting-started" ||
    pathname === "/forgot-password" ||
    pathname === "/reset-password";

  if (!token && !isPublicPage) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (token && isLoginPage) {
    return NextResponse.redirect(new URL("/actions", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
