interface OpenYakLogoProps {
  size?: number;
  className?: string;
}

export function OpenYakLogo({ size = 20, className }: OpenYakLogoProps) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/favicon.svg"
      width={size}
      height={size}
      alt="OpenYak"
      className={className}
      style={{ width: size, height: size }}
    />
  );
}
