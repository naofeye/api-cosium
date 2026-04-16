import { forwardRef, type SelectHTMLAttributes } from "react";

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

export type SelectOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

type SelectProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "children"> & {
  options: SelectOption[];
  placeholder?: string;
  error?: boolean;
};

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { options, placeholder, error, className, ...props },
  ref,
) {
  return (
    <select
      ref={ref}
      className={cn(
        "w-full rounded-lg border bg-white px-3 py-2.5 min-h-[44px] text-base sm:text-sm text-gray-900 shadow-sm transition-colors",
        "focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500",
        "disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400",
        error ? "border-red-400" : "border-gray-200",
        className,
      )}
      aria-invalid={error || undefined}
      {...props}
    >
      {placeholder && (
        <option value="" disabled>
          {placeholder}
        </option>
      )}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} disabled={opt.disabled}>
          {opt.label}
        </option>
      ))}
    </select>
  );
});
