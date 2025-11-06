"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
  rememberMe: z.boolean().default(false),
});

type LoginForm = z.infer<typeof loginSchema>;

function LoginPageInner() {
  const router = useRouter();
  const { login, isLoading: authLoading, error: authError, clearError, isAuthenticated } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      rememberMe: false,
    },
  });

  const rememberMe = watch("rememberMe");

  // Check for success message from registration
  useEffect(() => {
    // Remove searchParams dependency for now
    // const message = searchParams.get('message');
    // if (message) {
    //   setSuccessMessage(message);
    // }
  }, []);

  // Simple redirect after successful login
  useEffect(() => {
    if (isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, router]);

  // Clear errors when component mounts
  useEffect(() => {
    clearError();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const onSubmit = async (data: LoginForm) => {
    try {
      console.log('📝 Form submitted:', { email: data.email });
      await login({
        email: data.email,
        password: data.password,
        rememberMe: data.rememberMe,
      });
      
      console.log('✅ Login completed successfully');
      
      // Force immediate redirect after successful login
      console.log('🚀 Forcing immediate redirect...');
      setTimeout(() => {
        router.push("/dashboard");
      }, 100);
      
      // Backup redirect using window.location
      setTimeout(() => {
        if (window.location.pathname === '/login') {
          console.log('🔄 Using window.location fallback');
          window.location.href = '/dashboard';
        }
      }, 500);
      
    } catch (error) {
      // Error is handled by the auth context
      console.error("❌ Login failed:", error);
    }
  };

  return (
    <Card className="shadow-2xl border-0">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto mb-6 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
          <div className="h-6 w-6 rounded bg-blue-600"></div>
        </div>
        <CardTitle className="text-2xl font-bold text-gray-900">
          Welcome back
        </CardTitle>
        <p className="text-sm text-gray-600 mt-2">
          Sign in to your CostsHub account
        </p>
      </CardHeader>
      
      <CardContent className="pt-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {successMessage && (
            <div className="p-3 text-sm text-green-600 bg-green-50 border border-green-200 rounded-md">
              {successMessage}
            </div>
          )}
          
          {authError && (
            <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
              {authError}
            </div>
          )}
          
          <div className="space-y-2">
            <Label htmlFor="email" className="text-gray-700">
              Email address
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="Enter your email"
              {...register("email")}
              className={errors.email ? "border-red-500 focus-visible:ring-red-500" : ""}
              disabled={authLoading}
            />
            {errors.email && (
              <p className="text-sm text-red-600">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-gray-700">
              Password
            </Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                {...register("password")}
                className={errors.password ? "border-red-500 focus-visible:ring-red-500 pr-10" : "pr-10"}
                disabled={authLoading}
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                onClick={() => setShowPassword(!showPassword)}
                disabled={authLoading}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.password && (
              <p className="text-sm text-red-600">{errors.password.message}</p>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="rememberMe"
                checked={rememberMe}
                onCheckedChange={(checked) => setValue("rememberMe", !!checked)}
                disabled={authLoading}
              />
              <Label 
                htmlFor="rememberMe" 
                className="text-sm text-gray-600 cursor-pointer"
              >
                Remember me
              </Label>
            </div>
            <Link 
              href="/forgot-password" 
              className="text-sm text-blue-600 hover:text-blue-500 hover:underline"
            >
              Forgot password?
            </Link>
          </div>

          <Button 
            type="submit" 
            className="w-full" 
            disabled={authLoading}
            size="lg"
          >
            {authLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {authLoading ? "Signing in..." : "Sign in"}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            Don't have an account?{" "}
            <Link 
              href="/register" 
              className="font-medium text-blue-600 hover:text-blue-500 hover:underline"
            >
              Sign up
            </Link>
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LoginPageInner />
    </Suspense>
  );
}