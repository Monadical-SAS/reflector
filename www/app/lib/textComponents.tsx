type SimpleProps = {
  children: JSX.Element | string | (JSX.Element | string)[];
  className?: string;
};

const Title = ({ children, className }: SimpleProps) => (
  <h2 className={`text-lg md:text-xl ${className}`}>{children}</h2>
);
const Subtitle = ({ children, className }: SimpleProps) => (
  <h3 className={`text-base md:text-lg ${className}`}>{children}</h3>
);
const Paragraph = ({ children, className }: SimpleProps) => (
  <p className={`md:text-justify mb-2 md:mb-4 ${className}`}>{children}</p>
);

export { Title, Subtitle, Paragraph };
