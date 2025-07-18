import React, { useState } from "react";
import { Flex, Input, Button } from "@chakra-ui/react";

interface SearchBarProps {
  onSearch: (searchTerm: string) => void;
}

export default function SearchBar({ onSearch }: SearchBarProps) {
  const [searchInputValue, setSearchInputValue] = useState("");

  const handleSearch = () => {
    onSearch(searchInputValue);
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <Flex mb={4} alignItems="center">
      <Input
        placeholder="Search transcriptions..."
        value={searchInputValue}
        onChange={(e) => setSearchInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <Button ml={2} onClick={handleSearch}>
        Search
      </Button>
    </Flex>
  );
}
