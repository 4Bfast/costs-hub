"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Eye, EyeOff, Building2 } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

const registerSchema = z.object({
  organizationName: z.string().min(2, "Organization name must be at least 2 characters"),
  adminName: z.string().min(2, "Administrator name must be at least 2 characters"),
  adminEmail: z.string().email("Please enter a valid email address"),
  password: z.string()
    .min(8, "Password must be at least 8 characters")
    .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, "Password must contain at least one uppercase letter, one lowercase letter, and one number"),
  confirmPassword: z.string(),
  acceptTerms: z.boolean().refine(val => val === true, "You must accept the terms and conditions"),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { register: registerUser, isLoading: authLoading, error: authError, clearError, isAuthenticated } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      organizationName: "",
      adminName: "",
      adminEmail: "",
      password: "",
      confirmPassword: "",
      acceptTerms: false,
    },
  });

  const acceptTerms = watch("acceptTerms");
  const password = watch("password");

  const getPasswordStrength = (password: string) => {
    if (password.length === 0) return { strength: 0, label: "" };
    if (password.length < 6) return { strength: 1, label: "Weak" };
    if (password.length < 8) return { strength: 2, label: "Fair" };
    if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) return { strength: 2, label: "Fair" };
    return { strength: 3, label: "Strong" };
  };

  const passwordStrength = getPasswordStrength(password);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, router]);

  // Clear errors when component mounts
  useEffect(() => {
    clearError();
  }, [clearError]);

  const onSubmit = async (data: RegisterForm) => {
    try {
      await registerUser({
        organizationName: data.organizationName,
        adminName: data.adminName,
        adminEmail: data.adminEmail,
        password: data.password,
      });
      
      // Redirect to login with success message
      router.push("/login?message=Registration successful! Please check your email to verify your account.");
    } catch (error) {
      // Error is handled by the auth context
      console.error("Registration failed:", error);
    }
  };

  return (
    <Card className="shadow-2xl border-0 max-w-lg mx-auto">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto mb-6 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
          <Building2 className="h-6 w-6 text-blue-600" />
        </div>
        <CardTitle className="text-2xl font-bold text-gray-900">
          Create your organization
        </CardTitle>
        <p className="text-sm text-gray-600 mt-2">
          Start managing your multi-cloud costs with AI-powered analytics
        </p>
      </CardHeader>
      
      <CardContent className="pt-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {authError && (
            <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
              {authError}
            </div>
          )}
          
          <div className="space-y-2">
            <Label htmlFor="organizationName" className="text-gray-700">
              Organization Name
            </Label>
            <Input
              id="organizationName"
              placeholder="Enter your organization name"
              {...register("organizationName")}
              className={errors.organizationName ? "border-red-500 focus-visible:ring-red-500" : ""}
              disabled={authLoading}
            />
            {errors.organizationName && (
              <p className="text-sm text-red-600">{errors.organizationName.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="adminName" className="text-gray-700">
              Administrator Name
            </Label>
            <Input
              id="adminName"
              placeholder="Enter your full name"
              {...register("adminName")}
              className={errors.adminName ? "border-red-500 focus-visible:ring-red-500" : ""}
              disabled={authLoading}
            />
            {errors.adminName && (
              <p className="text-sm text-red-600">{errors.adminName.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="adminEmail" className="text-gray-700">
              Administrator Email
            </Label>
            <Input
              id="adminEmail"
              type="email"
              placeholder="Enter your email address"
              {...register("adminEmail")}
              className={errors.adminEmail ? "border-red-500 focus-visible:ring-red-500" : ""}
              disabled={authLoading}
            />
            {errors.adminEmail && (
              <p className="text-sm text-red-600">{errors.adminEmail.message}</p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="password" className="text-gray-700">
                Password
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Create a password"
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
              {password && (
                <div className="space-y-1">
                  <div className="flex space-x-1">
                    {[1, 2, 3].map((level) => (
                      <div
                        key={level}
                        className={`h-1 flex-1 rounded ${
                          level <= passwordStrength.strength
                            ? passwordStrength.strength === 1
                              ? "bg-red-500"
                              : passwordStrength.strength === 2
                              ? "bg-yellow-500"
                              : "bg-green-500"
                            : "bg-gray-200"
                        }`}
                      />
                    ))}
                  </div>
                  {passwordStrength.label && (
                    <p className={`text-xs ${
                      passwordStrength.strength === 1
                        ? "text-red-600"
                        : passwordStrength.strength === 2
                        ? "text-yellow-600"
                        : "text-green-600"
                    }`}>
                      {passwordStrength.label} password
                    </p>
                  )}
                </div>
              )}
              {errors.password && (
                <p className="text-sm text-red-600">{errors.password.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="text-gray-700">
                Confirm Password
              </Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="Confirm your password"
                  {...register("confirmPassword")}
                  className={errors.confirmPassword ? "border-red-500 focus-visible:ring-red-500 pr-10" : "pr-10"}
                  disabled={authLoading}
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  disabled={authLoading}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {errors.confirmPassword && (
                <p className="text-sm text-red-600">{errors.confirmPassword.message}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-start space-x-2">
              <Checkbox
                id="acceptTerms"
                checked={acceptTerms}
                onCheckedChange={(checked) => setValue("acceptTerms", !!checked)}
                disabled={authLoading}
                className="mt-1"
              />
              <Label 
                htmlFor="acceptTerms" 
                className="text-sm text-gray-600 cursor-pointer leading-relaxed"
              >
                I accept the{" "}
                <Link href="/terms" className="text-blue-600 hover:text-blue-500 hover:underline">
                  Terms of Service
                </Link>{" "}
                and{" "}
                <Link href="/privacy" className="text-blue-600 hover:text-blue-500 hover:underline">
                  Privacy Policy
                </Link>
              </Label>
            </div>
            {errors.acceptTerms && (
              <p className="text-sm text-red-600">{errors.acceptTerms.message}</p>
            )}
          </div>

          <Button 
            type="submit" 
            className="w-full" 
            disabled={authLoading}
            size="lg"
          >
            {authLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {authLoading ? "Creating account..." : "Create account"}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{" "}
            <Link 
              href="/login" 
              className="font-medium text-blue-600 hover:text-blue-500 hover:underline"
            >
              Sign in
            </Link>
          </p>
        </div>
      </CardContent>
    </Card>
  );
}