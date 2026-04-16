import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  leftIcon?: ReactNode;
  error?: boolean;
};

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { leftIcon, error, className, ...props },
  ref,
) {
  return (
    <div className="relative">
      {leftIcon && (
        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400" aria-hidden="true">
          {leftIcon}
        </span>
      )}
      <input
        ref={ref}
        className={cn(
          "w-full rounded-lg border bg-white px-3 py-2.5 min-h-[44px] text-base sm:text-sm text-gray-900 shadow-sm transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500",
          "disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400",
          leftIcon ? "pl-9" : "",
          error ? "border-red-400" : "border-gray-200",
          className,
        )}
        aria-invalid={error || undefined}
        {...props}
      />
    </div>
  );
});
