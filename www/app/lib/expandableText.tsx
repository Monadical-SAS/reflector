import type { BoxProps } from "@chakra-ui/react";
import { Box, Button, Text } from "@chakra-ui/react";
import React, { forwardRef, useState } from "react";

interface Props extends BoxProps {
  children: React.ReactNode;
  noOfLines: number;
}

export const ExpandableText = forwardRef<HTMLDivElement, Props>(
  ({ children, noOfLines, ...rest }, ref) => {
    const [expandedCount, setExpandedCount] = useState<number | undefined>(
      noOfLines,
    );
    const [isClicked, setIsClicked] = useState(false);
    const handleToggle = () => {
      setIsClicked(true);
      setExpandedCount(expandedCount ? undefined : noOfLines);
    };

    const inputRef = React.useRef<HTMLInputElement>(null);

    const isTextClamped =
      (inputRef.current?.scrollHeight as number) >
        (inputRef.current?.clientHeight as number) || isClicked;

    return (
      <Box ref={ref} {...rest}>
        <Box ref={inputRef} lineClamp={expandedCount}>
          {children}
        </Box>
        <Button
          display={isTextClamped ? "block" : "none"}
          size="sm"
          variant="link"
          onClick={handleToggle}
          mt={2}
        >
          <Text>{!expandedCount ? "Show less" : "Read more"}</Text>
        </Button>
      </Box>
    );
  },
);

ExpandableText.displayName = "ExpandableText";
