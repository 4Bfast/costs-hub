import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Authentication - CostsHub",
  description: "Sign in to your CostsHub account",
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-900 via-blue-800 to-blue-700 p-4">
      <div className="w-full max-w-md">
        {children}
      </div>
    </div>
  );
}