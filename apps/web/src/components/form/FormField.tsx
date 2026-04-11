"use client";

import { createContext, forwardRef, useContext, useId, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface FormFieldContextValue {
  fieldId: string;
  errorId: string | undefined;
}

const FormFieldContext = createContext<FormFieldContextValue | null>(null);

function useFormFieldContext(): FormFieldContextValue | null {
  return useContext(FormFieldContext);
}

interface FormFieldProps {
  label: string;
  required?: boolean;
  error?: string;
  children: ReactNode;
  className?: string;
  htmlFor?: string;
}

export function FormField({ label, required, error, children, className, htmlFor }: FormFieldProps) {
  const autoId = useId();
  const fieldId = htmlFor ?? autoId;
  const errorId = error ? `${fieldId}-error` : undefined;

  return (
    <FormFieldContext.Provider value={{ fieldId, errorId }}>
      <div className={className}>
        <label htmlFor={fieldId} className="mb-1.5 block text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-danger"> *</span>}
        </label>
        {children}
        {error && <p id={errorId} className="mt-1 text-xs text-danger" role="alert">{error}</p>}
      </div>
    </FormFieldContext.Provider>
  );
}

interface FormInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const FormInput = forwardRef<HTMLInputElement, FormInputProps>(function FormInput(
  { error, className, id: externalId, ...props },
  ref,
) {
  const ctx = useFormFieldContext();
  const inputId = externalId ?? ctx?.fieldId;
  const describedBy = ctx?.errorId ?? props["aria-describedby"];

  return (
    <input
      ref={ref}
      id={inputId}
      aria-describedby={describedBy}
      aria-invalid={error ? true : undefined}
      className={cn(
        "w-full rounded-lg border px-4 py-2.5 text-sm outline-none transition-colors focus:ring-2 focus:ring-blue-100 focus-visible:ring-2 focus-visible:ring-blue-500",
        error ? "border-danger focus:border-danger" : "border-border focus:border-primary",
        className,
      )}
      {...props}
    />
  );
});
