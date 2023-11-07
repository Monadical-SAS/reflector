type SimpleProps = {
  children: JSX.Element | string | (JSX.Element | string)[];
  className?: string;
};

const Title = ({ children }: SimpleProps) => (
  <h2 className="self-stretch font-semibold text-white mb-2 mt-8 text-2xl">
    {children}
  </h2>
);
const Subtitle = ({ children, className }: SimpleProps) => (
  <h3 className={`mb-1 text-white text-lg font-semibold ${className || ""}`}>
    {children}
  </h3>
);
const Paragraph = ({ children, className }: SimpleProps) => (
  <p className={`${className || ""} mb-1 md:mb-4 text-slate-300`}>{children}</p>
);

export { Title, Subtitle, Paragraph };
