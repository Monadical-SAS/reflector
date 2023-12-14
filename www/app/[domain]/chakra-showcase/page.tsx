"use client";
import {
  Grid,
  Box,
  Kbd,
  Heading,
  Text,
  Button,
  Wrap,
  WrapItem,
  Spinner,
  Menu,
  MenuList,
  MenuItem,
  MenuButton,
  Circle,
} from "@chakra-ui/react";
import { PhoneIcon, ChevronDownIcon } from "@chakra-ui/icons";
import { Select } from "chakra-react-select";
import supportedLanguages from "../../supportedLanguages";
import { useState } from "react";

export default () => {
  const [language, setLanguage] = useState<{ label: string; value: string }>({
    label: "No translation",
    value: "",
  });
  const options = supportedLanguages.map((i) => ({
    label: i.name,
    value: i.value || "",
  }));
  const handleLanguageChange = (option) => setLanguage(option);

  return (
    <>
      <div></div>
      <Grid
        templateColumns={{
          sm: "1fr",
          md: "repeat(2, 1fr)",
          lg: "repeat(2, 1fr)",
        }}
        templateRows={{ sm: "repeat(2, 1fr)", md: "1fr", lg: "1fr" }}
        gap={{ base: "2", md: "4", lg: "4" }}
        h="100%"
      >
        <Box
          bg="Background"
          h="100%"
          rounded="5px"
          p={{ base: "2", lg: "4" }}
          overflowX="scroll"
        >
          <Heading as="h1" size="xl" noOfLines={1}>
            Here are a few components
          </Heading>
          <Wrap spacing={4} p="4">
            <WrapItem>
              <span>
                <Kbd>shift</Kbd> + <Kbd>H</Kbd>
              </span>
            </WrapItem>
            <WrapItem>
              <Circle size="40px" bg="tomato" color="white">
                <PhoneIcon />
              </Circle>
            </WrapItem>
            <WrapItem>
              <Button colorScheme="blue">A button</Button>
            </WrapItem>

            <WrapItem>
              <Spinner />
            </WrapItem>

            <WrapItem>
              <Menu>
                <MenuButton as={Button} rightIcon={<ChevronDownIcon />}>
                  Actions
                </MenuButton>
                <MenuList>
                  <MenuItem>Download</MenuItem>
                  <MenuItem>Create a Copy</MenuItem>
                  <MenuItem>Mark as Draft</MenuItem>
                  <MenuItem>Delete</MenuItem>
                  <MenuItem>Attend a Workshop</MenuItem>
                </MenuList>
              </Menu>
            </WrapItem>
          </Wrap>
          <WrapItem>
            <Select
              options={options}
              onChange={handleLanguageChange}
              value={language}
            />
          </WrapItem>
        </Box>
        <Box
          bg="Background"
          h="100%"
          rounded="5px"
          p={{ base: "2", lg: "4" }}
          overflowX="scroll"
        >
          <Text>
            All legths can be either a number that maps to default values (eg
            '2' will become '--var-chakra-space-2', which by default is .5rem),
            a css string value like "25px" or an object with different values
            for different screen sizes. See the docs on responsive-styles.
          </Text>
          <Text>
            This is the default theme, but you can ovewrite part or all of it,
            see the Customize Component styles section of the docs, especially
            Customizing component styles
          </Text>
          <Text>I think the figma section of their docs is promising too</Text>
        </Box>
      </Grid>
    </>
  );
};
