-- 3D-only Battlemon catalog. Deploy paired eDBCs/client assets before starting the server.
-- Existing species keep their existing moves; new appearances copy matching form overrides.
CREATE TEMPORARY TABLE `bm3d_forms` LIKE `battlemon_forms`;
DELETE FROM `bm3d_forms`;
INSERT INTO `bm3d_forms` (`id`, `species_id`, `sprite`, `variant`, `name`, `back_sprite`) VALUES
('2000', '1033', 'BM3D_2000', 'pixelmon:base:none:always', 'MissingNo', 'BM3D_2000'),
('2001', '2', 'BM3D_2001', 'pixelmon:base:halloween:always', 'Ivysaur (Halloween)', 'BM3D_2001'),
('2002', '3', 'BM3D_2002', 'pixelmon:base:zombie:always', 'Venusaur (Zombie)', 'BM3D_2002'),
('2003', '3', 'BM3D_2003', 'pixelmon:gmax:none:always', 'Venusaur (Gmax)', 'BM3D_2003'),
('2005', '3', 'BM3D_2005', 'pixelmon:gmax:zombie:always', 'Venusaur (Gmax, Zombie)', 'BM3D_2005'),
('2006', '4', 'BM3D_2006', 'pixelmon:base:none:always', 'Charmander', 'BM3D_2006'),
('2008', '5', 'BM3D_2008', 'pixelmon:base:none:always', 'Charmeleon', 'BM3D_2008'),
('2010', '6', 'BM3D_2010', 'pixelmon:base:none:flying', 'Charizard (Flying)', 'BM3D_2010'),
('2011', '6', 'BM3D_2011', 'pixelmon:base:none:always', 'Charizard (State 1)', 'BM3D_2011'),
('2014', '6', 'BM3D_2014', 'pixelmon:base:zombie:flying', 'Charizard (Zombie, Flying)', 'BM3D_2014'),
('2015', '6', 'BM3D_2015', 'pixelmon:base:zombie:always', 'Charizard (Zombie, State 1)', 'BM3D_2015'),
('2016', '6', 'BM3D_2016', 'pixelmon:gmax:none:always', 'Charizard (Gmax)', 'BM3D_2016'),
('2018', '6', 'BM3D_2018', 'pixelmon:gmax:zombie:always', 'Charizard (Gmax, Zombie)', 'BM3D_2018'),
('2019', '9', 'BM3D_2019', 'pixelmon:base:zombie:always', 'Blastoise (Zombie)', 'BM3D_2019'),
('2020', '9', 'BM3D_2020', 'pixelmon:gmax:none:always', 'Blastoise (Gmax)', 'BM3D_2020'),
('2022', '9', 'BM3D_2022', 'pixelmon:gmax:zombie:always', 'Blastoise (Gmax, Zombie)', 'BM3D_2022'),
('2023', '10', 'BM3D_2023', 'pixelmon:base:pink:always', 'Caterpie (Pink)', 'BM3D_2023'),
('2024', '10', 'BM3D_2024', 'pixelmon:base:valencian:always', 'Caterpie (Valencian)', 'BM3D_2024'),
('2025', '11', 'BM3D_2025', 'pixelmon:base:pink:always', 'Metapod (Pink)', 'BM3D_2025'),
('2026', '11', 'BM3D_2026', 'pixelmon:base:valencian:always', 'Metapod (Valencian)', 'BM3D_2026'),
('2027', '12', 'BM3D_2027', 'pixelmon:base:pink:flying', 'Butterfree (Pink, Flying)', 'BM3D_2027'),
('2028', '12', 'BM3D_2028', 'pixelmon:base:pink:always', 'Butterfree (Pink, State 1)', 'BM3D_2028'),
('2029', '12', 'BM3D_2029', 'pixelmon:base:valencian:flying', 'Butterfree (Valencian, Flying)', 'BM3D_2029'),
('2030', '12', 'BM3D_2030', 'pixelmon:base:valencian:always', 'Butterfree (Valencian, State 1)', 'BM3D_2030'),
('2031', '12', 'BM3D_2031', 'pixelmon:gmax:none:always', 'Butterfree (Gmax)', 'BM3D_2031'),
('2032', '12', 'BM3D_2032', 'pixelmon:gmax:pink:always', 'Butterfree (Gmax, Pink)', 'BM3D_2032'),
('2034', '12', 'BM3D_2034', 'pixelmon:gmax:valencian:always', 'Butterfree (Gmax, Valencian)', 'BM3D_2034'),
('2035', '13', 'BM3D_2035', 'pixelmon:base:pink:always', 'Weedle (Pink)', 'BM3D_2035'),
('2036', '14', 'BM3D_2036', 'pixelmon:base:pink:always', 'Kakuna (Pink)', 'BM3D_2036'),
('2037', '15', 'BM3D_2037', 'pixelmon:base:pink:always', 'Beedrill (Pink)', 'BM3D_2037'),
('2038', '16', 'BM3D_2038', 'pixelmon:base:none:flying', 'Pidgey (Flying)', 'BM3D_2038'),
('2039', '16', 'BM3D_2039', 'pixelmon:base:pink:flying', 'Pidgey (Pink, Flying)', 'BM3D_2039'),
('2040', '16', 'BM3D_2040', 'pixelmon:base:pink:always', 'Pidgey (Pink, State 1)', 'BM3D_2040'),
('2042', '17', 'BM3D_2042', 'pixelmon:base:none:flying', 'Pidgeotto (Flying)', 'BM3D_2042'),
('2043', '17', 'BM3D_2043', 'pixelmon:base:pink:flying', 'Pidgeotto (Pink, Flying)', 'BM3D_2043'),
('2044', '17', 'BM3D_2044', 'pixelmon:base:pink:always', 'Pidgeotto (Pink, State 1)', 'BM3D_2044'),
('2046', '18', 'BM3D_2046', 'pixelmon:base:none:flying', 'Pidgeot (Flying)', 'BM3D_2046'),
('2047', '18', 'BM3D_2047', 'pixelmon:base:pink:flying', 'Pidgeot (Pink, Flying)', 'BM3D_2047'),
('2048', '18', 'BM3D_2048', 'pixelmon:base:pink:always', 'Pidgeot (Pink, State 1)', 'BM3D_2048'),
('2050', '19', 'BM3D_2050', 'pixelmon:base:pink:always', 'Rattata (Pink)', 'BM3D_2050'),
('2051', '19', 'BM3D_2051', 'pixelmon:base:valencian:always', 'Rattata (Valencian)', 'BM3D_2051'),
('2052', '20', 'BM3D_2052', 'pixelmon:base:pink:always', 'Raticate (Pink)', 'BM3D_2052'),
('2053', '20', 'BM3D_2053', 'pixelmon:base:valencian:always', 'Raticate (Valencian)', 'BM3D_2053'),
('2054', '21', 'BM3D_2054', 'pixelmon:base:none:flying', 'Spearow (Flying)', 'BM3D_2054'),
('2056', '24', 'BM3D_2056', 'pixelmon:base:dark:always', 'Arbok (Dark)', 'BM3D_2056'),
('2057', '24', 'BM3D_2057', 'pixelmon:base:main_circular:always', 'Arbok (Main Circular)', 'BM3D_2057'),
('2058', '24', 'BM3D_2058', 'pixelmon:base:secondary_circular:always', 'Arbok (Secondary Circular)', 'BM3D_2058'),
('2059', '25', 'BM3D_2059', 'pixelmon:base:christmas:always', 'Pikachu (Christmas)', 'BM3D_2059'),
('2060', '25', 'BM3D_2060', 'pixelmon:base:drowned:always', 'Pikachu (Drowned)', 'BM3D_2060'),
('2061', '25', 'BM3D_2061', 'pixelmon:base:elf:always', 'Pikachu (Elf)', 'BM3D_2061'),
('2062', '25', 'BM3D_2062', 'pixelmon:gmax:none:always', 'Pikachu (Gmax)', 'BM3D_2062'),
('2064', '26', 'BM3D_2064', 'pixelmon:alolan:summer:always', 'Raichu (Alolan, Summer)', 'BM3D_2064'),
('2065', '26', 'BM3D_2065', 'pixelmon:base:christmas:always', 'Raichu (Christmas)', 'BM3D_2065'),
('2066', '26', 'BM3D_2066', 'pixelmon:base:elf:always', 'Raichu (Elf)', 'BM3D_2066'),
('2067', '27', 'BM3D_2067', 'pixelmon:alolan:christmas:always', 'Sandshrew (Alolan, Christmas)', 'BM3D_2067'),
('2068', '28', 'BM3D_2068', 'pixelmon:alolan:christmas:always', 'Sandslash (Alolan, Christmas)', 'BM3D_2068'),
('2069', '29', 'BM3D_2069', 'pixelmon:base:pink:always', 'Nidoranfemale (Pink)', 'BM3D_2069'),
('2070', '29', 'BM3D_2070', 'pixelmon:base:valencian:always', 'Nidoranfemale (Valencian)', 'BM3D_2070'),
('2071', '30', 'BM3D_2071', 'pixelmon:base:pink:always', 'Nidorina (Pink)', 'BM3D_2071'),
('2072', '30', 'BM3D_2072', 'pixelmon:base:valencian:always', 'Nidorina (Valencian)', 'BM3D_2072'),
('2073', '31', 'BM3D_2073', 'pixelmon:base:pink:always', 'Nidoqueen (Pink)', 'BM3D_2073'),
('2074', '31', 'BM3D_2074', 'pixelmon:base:valencian:always', 'Nidoqueen (Valencian)', 'BM3D_2074'),
('2075', '32', 'BM3D_2075', 'pixelmon:base:pink:always', 'Nidoranmale (Pink)', 'BM3D_2075'),
('2076', '32', 'BM3D_2076', 'pixelmon:base:valencian:always', 'Nidoranmale (Valencian)', 'BM3D_2076'),
('2077', '33', 'BM3D_2077', 'pixelmon:base:pink:always', 'Nidorino (Pink)', 'BM3D_2077'),
('2078', '33', 'BM3D_2078', 'pixelmon:base:valencian:always', 'Nidorino (Valencian)', 'BM3D_2078'),
('2079', '34', 'BM3D_2079', 'pixelmon:base:pink:always', 'Nidoking (Pink)', 'BM3D_2079'),
('2080', '34', 'BM3D_2080', 'pixelmon:base:valencian:always', 'Nidoking (Valencian)', 'BM3D_2080'),
('2081', '37', 'BM3D_2081', 'pixelmon:alolan:christmas:always', 'Vulpix (Alolan, Christmas)', 'BM3D_2081'),
('2082', '37', 'BM3D_2082', 'pixelmon:base:strike:always', 'Vulpix (Strike)', 'BM3D_2082'),
('2083', '38', 'BM3D_2083', 'pixelmon:alolan:christmas:always', 'Ninetales (Alolan, Christmas)', 'BM3D_2083'),
('2084', '38', 'BM3D_2084', 'pixelmon:base:strike:always', 'Ninetales (Strike)', 'BM3D_2084'),
('2085', '41', 'BM3D_2085', 'pixelmon:base:strike:always', 'Zubat (Strike)', 'BM3D_2085'),
('2086', '42', 'BM3D_2086', 'pixelmon:base:strike:always', 'Golbat (Strike)', 'BM3D_2086'),
('2087', '43', 'BM3D_2087', 'pixelmon:base:pink:always', 'Oddish (Pink)', 'BM3D_2087'),
('2088', '43', 'BM3D_2088', 'pixelmon:base:valencian:always', 'Oddish (Valencian)', 'BM3D_2088'),
('2089', '44', 'BM3D_2089', 'pixelmon:base:pink:always', 'Gloom (Pink)', 'BM3D_2089'),
('2090', '44', 'BM3D_2090', 'pixelmon:base:valencian:always', 'Gloom (Valencian)', 'BM3D_2090'),
('2091', '45', 'BM3D_2091', 'pixelmon:base:pink:always', 'Vileplume (Pink)', 'BM3D_2091'),
('2092', '45', 'BM3D_2092', 'pixelmon:base:valencian:always', 'Vileplume (Valencian)', 'BM3D_2092'),
('2093', '46', 'BM3D_2093', 'pixelmon:base:pink:always', 'Paras (Pink)', 'BM3D_2093'),
('2094', '46', 'BM3D_2094', 'pixelmon:base:valencian:always', 'Paras (Valencian)', 'BM3D_2094'),
('2095', '47', 'BM3D_2095', 'pixelmon:base:pink:always', 'Parasect (Pink)', 'BM3D_2095'),
('2096', '47', 'BM3D_2096', 'pixelmon:base:valencian:always', 'Parasect (Valencian)', 'BM3D_2096'),
('2097', '48', 'BM3D_2097', 'pixelmon:base:pink:always', 'Venonat (Pink)', 'BM3D_2097'),
('2098', '49', 'BM3D_2098', 'pixelmon:base:pink:always', 'Venomoth (Pink)', 'BM3D_2098'),
('2099', '50', 'BM3D_2099', 'pixelmon:base:pink:always', 'Diglett (Pink)', 'BM3D_2099'),
('2100', '51', 'BM3D_2100', 'pixelmon:base:pink:always', 'Dugtrio (Pink)', 'BM3D_2100'),
('2101', '52', 'BM3D_2101', 'pixelmon:gmax:none:always', 'Meowth (Gmax)', 'BM3D_2101'),
('2103', '56', 'BM3D_2103', 'pixelmon:base:pink:always', 'Mankey (Pink)', 'BM3D_2103'),
('2104', '57', 'BM3D_2104', 'pixelmon:base:pink:always', 'Primeape (Pink)', 'BM3D_2104'),
('2105', '59', 'BM3D_2105', 'pixelmon:base:ashen:always', 'Arcanine (Ashen)', 'BM3D_2105'),
('2106', '59', 'BM3D_2106', 'pixelmon:base:zombie:always', 'Arcanine (Zombie)', 'BM3D_2106'),
('2107', '60', 'BM3D_2107', 'pixelmon:base:valencian:always', 'Poliwag (Valencian)', 'BM3D_2107'),
('2108', '61', 'BM3D_2108', 'pixelmon:base:valencian:always', 'Poliwhirl (Valencian)', 'BM3D_2108'),
('2109', '62', 'BM3D_2109', 'pixelmon:base:strike:always', 'Poliwrath (Strike)', 'BM3D_2109'),
('2110', '62', 'BM3D_2110', 'pixelmon:base:valencian:always', 'Poliwrath (Valencian)', 'BM3D_2110'),
('2111', '68', 'BM3D_2111', 'pixelmon:gmax:none:always', 'Machamp (Gmax)', 'BM3D_2111'),
('2113', '69', 'BM3D_2113', 'pixelmon:base:pink:always', 'Bellsprout (Pink)', 'BM3D_2113'),
('2114', '69', 'BM3D_2114', 'pixelmon:base:valencian:always', 'Bellsprout (Valencian)', 'BM3D_2114'),
('2115', '70', 'BM3D_2115', 'pixelmon:base:pink:always', 'Weepinbell (Pink)', 'BM3D_2115'),
('2116', '70', 'BM3D_2116', 'pixelmon:base:valencian:always', 'Weepinbell (Valencian)', 'BM3D_2116'),
('2117', '71', 'BM3D_2117', 'pixelmon:base:pink:always', 'Victreebel (Pink)', 'BM3D_2117'),
('2118', '71', 'BM3D_2118', 'pixelmon:base:valencian:always', 'Victreebel (Valencian)', 'BM3D_2118'),
('2119', '73', 'BM3D_2119', 'pixelmon:base:drowned:always', 'Tentacruel (Drowned)', 'BM3D_2119'),
('2120', '77', 'BM3D_2120', 'pixelmon:base:rainbow:always', 'Ponyta (Rainbow)', 'BM3D_2120'),
('2121', '78', 'BM3D_2121', 'pixelmon:base:drowned:always', 'Rapidash (Drowned)', 'BM3D_2121'),
('2122', '78', 'BM3D_2122', 'pixelmon:base:rainbow:always', 'Rapidash (Rainbow)', 'BM3D_2122'),
('2123', '84', 'BM3D_2123', 'pixelmon:base:pink:always', 'Doduo (Pink)', 'BM3D_2123'),
('2124', '85', 'BM3D_2124', 'pixelmon:base:pink:always', 'Dodrio (Pink)', 'BM3D_2124'),
('2125', '90', 'BM3D_2125', 'pixelmon:base:valencian:always', 'Shellder (Valencian)', 'BM3D_2125'),
('2126', '91', 'BM3D_2126', 'pixelmon:base:valencian:always', 'Cloyster (Valencian)', 'BM3D_2126'),
('2127', '92', 'BM3D_2127', 'pixelmon:base:online:always', 'Gastly (Online)', 'BM3D_2127'),
('2128', '93', 'BM3D_2128', 'pixelmon:base:online:always', 'Haunter (Online)', 'BM3D_2128'),
('2129', '94', 'BM3D_2129', 'pixelmon:base:ashen:always', 'Gengar (Ashen)', 'BM3D_2129'),
('2130', '94', 'BM3D_2130', 'pixelmon:base:online:always', 'Gengar (Online)', 'BM3D_2130'),
('2131', '94', 'BM3D_2131', 'pixelmon:gmax:ashen:always', 'Gengar (Gmax, Ashen)', 'BM3D_2131'),
('2132', '94', 'BM3D_2132', 'pixelmon:gmax:none:always', 'Gengar (Gmax)', 'BM3D_2132'),
('2133', '94', 'BM3D_2133', 'pixelmon:gmax:online:always', 'Gengar (Gmax, Online)', 'BM3D_2133'),
('2135', '95', 'BM3D_2135', 'pixelmon:base:crystal:always', 'Onix (Crystal)', 'BM3D_2135'),
('2136', '99', 'BM3D_2136', 'pixelmon:gmax:none:always', 'Kingler (Gmax)', 'BM3D_2136'),
('2138', '101', 'BM3D_2138', 'pixelmon:base:summer:always', 'Electrode (Summer)', 'BM3D_2138'),
('2139', '102', 'BM3D_2139', 'pixelmon:base:pink:always', 'Exeggcute (Pink)', 'BM3D_2139'),
('2140', '103', 'BM3D_2140', 'pixelmon:base:pink:always', 'Exeggutor (Pink)', 'BM3D_2140'),
('2141', '109', 'BM3D_2141', 'pixelmon:base:valentine:always', 'Koffing (Valentine)', 'BM3D_2141'),
('2142', '110', 'BM3D_2142', 'pixelmon:base:valentine:always', 'Weezing (Valentine)', 'BM3D_2142'),
('2143', '111', 'BM3D_2143', 'pixelmon:base:pink:always', 'Rhyhorn (Pink)', 'BM3D_2143'),
('2144', '112', 'BM3D_2144', 'pixelmon:base:pink:always', 'Rhydon (Pink)', 'BM3D_2144'),
('2145', '113', 'BM3D_2145', 'pixelmon:base:valencian:always', 'Chansey (Valencian)', 'BM3D_2145'),
('2146', '121', 'BM3D_2146', 'pixelmon:base:drowned:always', 'Starmie (Drowned)', 'BM3D_2146'),
('2147', '121', 'BM3D_2147', 'pixelmon:mega:patrick:always', 'Starmie (Mega, Patrick)', 'BM3D_2147'),
('2148', '126', 'BM3D_2148', 'pixelmon:base:calcium_carbonate:always', 'Magmar (Calcium Carbonate)', 'BM3D_2148'),
('2149', '126', 'BM3D_2149', 'pixelmon:base:copper_sulfate:always', 'Magmar (Copper Sulfate)', 'BM3D_2149'),
('2150', '126', 'BM3D_2150', 'pixelmon:base:cupric_chloride:always', 'Magmar (Cupric Chloride)', 'BM3D_2150'),
('2151', '126', 'BM3D_2151', 'pixelmon:base:lithium_chloride:always', 'Magmar (Lithium Chloride)', 'BM3D_2151'),
('2152', '126', 'BM3D_2152', 'pixelmon:base:magnesium_sulfide:always', 'Magmar (Magnesium Sulfide)', 'BM3D_2152'),
('2153', '126', 'BM3D_2153', 'pixelmon:base:manganese_chloride:always', 'Magmar (Manganese Chloride)', 'BM3D_2153'),
('2154', '126', 'BM3D_2154', 'pixelmon:base:potassium_chloride:always', 'Magmar (Potassium Chloride)', 'BM3D_2154'),
('2155', '126', 'BM3D_2155', 'pixelmon:base:sodium_carbonate:always', 'Magmar (Sodium Carbonate)', 'BM3D_2155'),
('2156', '129', 'BM3D_2156', 'pixelmon:base:apricot_stripes:always', 'Magikarp (Apricot Stripes, Female)', 'BM3D_2156'),
('2157', '129', 'BM3D_2157', 'pixelmon:base:apricot_tiger:always', 'Magikarp (Apricot Tiger, Female)', 'BM3D_2157'),
('2158', '129', 'BM3D_2158', 'pixelmon:base:apricot_zebra:always', 'Magikarp (Apricot Zebra, Female)', 'BM3D_2158'),
('2159', '129', 'BM3D_2159', 'pixelmon:base:black_forehead:always', 'Magikarp (Black Forehead, Female)', 'BM3D_2159'),
('2160', '129', 'BM3D_2160', 'pixelmon:base:black_mask:always', 'Magikarp (Black Mask, Female)', 'BM3D_2160'),
('2161', '129', 'BM3D_2161', 'pixelmon:base:blue_raindrops:always', 'Magikarp (Blue Raindrops, Female)', 'BM3D_2161'),
('2162', '129', 'BM3D_2162', 'pixelmon:base:blue_saucy:always', 'Magikarp (Blue Saucy, Female)', 'BM3D_2162'),
('2163', '129', 'BM3D_2163', 'pixelmon:base:brown_stripes:always', 'Magikarp (Brown Stripes, Female)', 'BM3D_2163'),
('2164', '129', 'BM3D_2164', 'pixelmon:base:brown_tiger:always', 'Magikarp (Brown Tiger, Female)', 'BM3D_2164'),
('2165', '129', 'BM3D_2165', 'pixelmon:base:brown_zebra:always', 'Magikarp (Brown Zebra, Female)', 'BM3D_2165'),
('2166', '129', 'BM3D_2166', 'pixelmon:base:calico_orange_gold:always', 'Magikarp (Calico Orange Gold, Female)', 'BM3D_2166'),
('2167', '129', 'BM3D_2167', 'pixelmon:base:calico_orange_white:always', 'Magikarp (Calico Orange White, Female)', 'BM3D_2167'),
('2168', '129', 'BM3D_2168', 'pixelmon:base:calico_orange_white_black:always', 'Magikarp (Calico Orange White Black, Female)', 'BM3D_2168'),
('2169', '129', 'BM3D_2169', 'pixelmon:base:calico_white_orange:always', 'Magikarp (Calico White Orange, Female)', 'BM3D_2169'),
('2170', '129', 'BM3D_2170', 'pixelmon:base:gray_bubbles:always', 'Magikarp (Gray Bubbles, Female)', 'BM3D_2170'),
('2171', '129', 'BM3D_2171', 'pixelmon:base:gray_diamonds:always', 'Magikarp (Gray Diamonds, Female)', 'BM3D_2171'),
('2172', '129', 'BM3D_2172', 'pixelmon:base:gray_patches:always', 'Magikarp (Gray Patches, Female)', 'BM3D_2172'),
('2173', '129', 'BM3D_2173', 'pixelmon:base:orange_dapples:always', 'Magikarp (Orange Dapples, Female)', 'BM3D_2173'),
('2174', '129', 'BM3D_2174', 'pixelmon:base:orange_forehead:always', 'Magikarp (Orange Forehead, Female)', 'BM3D_2174'),
('2175', '129', 'BM3D_2175', 'pixelmon:base:orange_mask:always', 'Magikarp (Orange Mask, Female)', 'BM3D_2175'),
('2176', '129', 'BM3D_2176', 'pixelmon:base:orange_orca:always', 'Magikarp (Orange Orca, Female)', 'BM3D_2176'),
('2177', '129', 'BM3D_2177', 'pixelmon:base:orange_twotone:always', 'Magikarp (Orange Twotone, Female)', 'BM3D_2177'),
('2178', '129', 'BM3D_2178', 'pixelmon:base:pink_dapples:always', 'Magikarp (Pink Dapples, Female)', 'BM3D_2178'),
('2179', '129', 'BM3D_2179', 'pixelmon:base:pink_orca:always', 'Magikarp (Pink Orca, Female)', 'BM3D_2179'),
('2180', '129', 'BM3D_2180', 'pixelmon:base:pink_twotone:always', 'Magikarp (Pink Twotone, Female)', 'BM3D_2180'),
('2181', '129', 'BM3D_2181', 'pixelmon:base:purple_bubbles:always', 'Magikarp (Purple Bubbles, Female)', 'BM3D_2181'),
('2182', '129', 'BM3D_2182', 'pixelmon:base:purple_diamonds:always', 'Magikarp (Purple Diamonds, Female)', 'BM3D_2182'),
('2183', '129', 'BM3D_2183', 'pixelmon:base:purple_patches:always', 'Magikarp (Purple Patches, Female)', 'BM3D_2183'),
('2184', '129', 'BM3D_2184', 'pixelmon:base:roasted:always', 'Magikarp (Roasted, Female)', 'BM3D_2184'),
('2185', '129', 'BM3D_2185', 'pixelmon:base:skelly:always', 'Magikarp (Skelly, Female)', 'BM3D_2185'),
('2186', '129', 'BM3D_2186', 'pixelmon:base:valencian:always', 'Magikarp (Valencian, Female)', 'BM3D_2186'),
('2187', '129', 'BM3D_2187', 'pixelmon:base:violet_raindrops:always', 'Magikarp (Violet Raindrops, Female)', 'BM3D_2187'),
('2188', '129', 'BM3D_2188', 'pixelmon:base:violet_saucy:always', 'Magikarp (Violet Saucy, Female)', 'BM3D_2188'),
('2189', '129', 'BM3D_2189', 'pixelmon:base:apricot_stripes:always', 'Magikarp (Apricot Stripes, Male)', 'BM3D_2189'),
('2190', '129', 'BM3D_2190', 'pixelmon:base:apricot_tiger:always', 'Magikarp (Apricot Tiger, Male)', 'BM3D_2190'),
('2191', '129', 'BM3D_2191', 'pixelmon:base:apricot_zebra:always', 'Magikarp (Apricot Zebra, Male)', 'BM3D_2191'),
('2192', '129', 'BM3D_2192', 'pixelmon:base:black_forehead:always', 'Magikarp (Black Forehead, Male)', 'BM3D_2192'),
('2193', '129', 'BM3D_2193', 'pixelmon:base:black_mask:always', 'Magikarp (Black Mask, Male)', 'BM3D_2193'),
('2194', '129', 'BM3D_2194', 'pixelmon:base:blue_raindrops:always', 'Magikarp (Blue Raindrops, Male)', 'BM3D_2194'),
('2195', '129', 'BM3D_2195', 'pixelmon:base:blue_saucy:always', 'Magikarp (Blue Saucy, Male)', 'BM3D_2195'),
('2196', '129', 'BM3D_2196', 'pixelmon:base:brown_stripes:always', 'Magikarp (Brown Stripes, Male)', 'BM3D_2196'),
('2197', '129', 'BM3D_2197', 'pixelmon:base:brown_tiger:always', 'Magikarp (Brown Tiger, Male)', 'BM3D_2197'),
('2198', '129', 'BM3D_2198', 'pixelmon:base:brown_zebra:always', 'Magikarp (Brown Zebra, Male)', 'BM3D_2198'),
('2199', '129', 'BM3D_2199', 'pixelmon:base:calico_orange_gold:always', 'Magikarp (Calico Orange Gold, Male)', 'BM3D_2199'),
('2200', '129', 'BM3D_2200', 'pixelmon:base:calico_orange_white:always', 'Magikarp (Calico Orange White, Male)', 'BM3D_2200'),
('2201', '129', 'BM3D_2201', 'pixelmon:base:calico_orange_white_black:always', 'Magikarp (Calico Orange White Black, Male)', 'BM3D_2201'),
('2202', '129', 'BM3D_2202', 'pixelmon:base:calico_white_orange:always', 'Magikarp (Calico White Orange, Male)', 'BM3D_2202'),
('2203', '129', 'BM3D_2203', 'pixelmon:base:gray_bubbles:always', 'Magikarp (Gray Bubbles, Male)', 'BM3D_2203'),
('2204', '129', 'BM3D_2204', 'pixelmon:base:gray_diamonds:always', 'Magikarp (Gray Diamonds, Male)', 'BM3D_2204'),
('2205', '129', 'BM3D_2205', 'pixelmon:base:gray_patches:always', 'Magikarp (Gray Patches, Male)', 'BM3D_2205'),
('2206', '129', 'BM3D_2206', 'pixelmon:base:orange_dapples:always', 'Magikarp (Orange Dapples, Male)', 'BM3D_2206'),
('2207', '129', 'BM3D_2207', 'pixelmon:base:orange_forehead:always', 'Magikarp (Orange Forehead, Male)', 'BM3D_2207'),
('2208', '129', 'BM3D_2208', 'pixelmon:base:orange_mask:always', 'Magikarp (Orange Mask, Male)', 'BM3D_2208'),
('2209', '129', 'BM3D_2209', 'pixelmon:base:orange_orca:always', 'Magikarp (Orange Orca, Male)', 'BM3D_2209'),
('2210', '129', 'BM3D_2210', 'pixelmon:base:orange_twotone:always', 'Magikarp (Orange Twotone, Male)', 'BM3D_2210'),
('2211', '129', 'BM3D_2211', 'pixelmon:base:pink_dapples:always', 'Magikarp (Pink Dapples, Male)', 'BM3D_2211'),
('2212', '129', 'BM3D_2212', 'pixelmon:base:pink_orca:always', 'Magikarp (Pink Orca, Male)', 'BM3D_2212'),
('2213', '129', 'BM3D_2213', 'pixelmon:base:pink_twotone:always', 'Magikarp (Pink Twotone, Male)', 'BM3D_2213'),
('2214', '129', 'BM3D_2214', 'pixelmon:base:purple_bubbles:always', 'Magikarp (Purple Bubbles, Male)', 'BM3D_2214'),
('2215', '129', 'BM3D_2215', 'pixelmon:base:purple_diamonds:always', 'Magikarp (Purple Diamonds, Male)', 'BM3D_2215'),
('2216', '129', 'BM3D_2216', 'pixelmon:base:purple_patches:always', 'Magikarp (Purple Patches, Male)', 'BM3D_2216'),
('2217', '129', 'BM3D_2217', 'pixelmon:base:roasted:always', 'Magikarp (Roasted, Male)', 'BM3D_2217'),
('2218', '129', 'BM3D_2218', 'pixelmon:base:skelly:always', 'Magikarp (Skelly, Male)', 'BM3D_2218'),
('2219', '129', 'BM3D_2219', 'pixelmon:base:valencian:always', 'Magikarp (Valencian, Male)', 'BM3D_2219'),
('2220', '129', 'BM3D_2220', 'pixelmon:base:violet_raindrops:always', 'Magikarp (Violet Raindrops, Male)', 'BM3D_2220'),
('2221', '129', 'BM3D_2221', 'pixelmon:base:violet_saucy:always', 'Magikarp (Violet Saucy, Male)', 'BM3D_2221'),
('2222', '130', 'BM3D_2222', 'pixelmon:base:apricot_stripes:always', 'Gyarados (Apricot Stripes)', 'BM3D_2222'),
('2223', '130', 'BM3D_2223', 'pixelmon:base:apricot_tiger:always', 'Gyarados (Apricot Tiger)', 'BM3D_2223'),
('2224', '130', 'BM3D_2224', 'pixelmon:base:apricot_zebra:always', 'Gyarados (Apricot Zebra)', 'BM3D_2224'),
('2225', '130', 'BM3D_2225', 'pixelmon:base:black_forehead:always', 'Gyarados (Black Forehead)', 'BM3D_2225'),
('2226', '130', 'BM3D_2226', 'pixelmon:base:black_mask:always', 'Gyarados (Black Mask)', 'BM3D_2226'),
('2227', '130', 'BM3D_2227', 'pixelmon:base:blue_raindrops:always', 'Gyarados (Blue Raindrops)', 'BM3D_2227'),
('2228', '130', 'BM3D_2228', 'pixelmon:base:blue_saucy:always', 'Gyarados (Blue Saucy)', 'BM3D_2228'),
('2229', '130', 'BM3D_2229', 'pixelmon:base:brown_stripes:always', 'Gyarados (Brown Stripes)', 'BM3D_2229'),
('2230', '130', 'BM3D_2230', 'pixelmon:base:brown_tiger:always', 'Gyarados (Brown Tiger)', 'BM3D_2230'),
('2231', '130', 'BM3D_2231', 'pixelmon:base:brown_zebra:always', 'Gyarados (Brown Zebra)', 'BM3D_2231'),
('2232', '130', 'BM3D_2232', 'pixelmon:base:calico_orange_gold:always', 'Gyarados (Calico Orange Gold)', 'BM3D_2232'),
('2233', '130', 'BM3D_2233', 'pixelmon:base:calico_orange_white:always', 'Gyarados (Calico Orange White)', 'BM3D_2233'),
('2234', '130', 'BM3D_2234', 'pixelmon:base:calico_orange_white_black:always', 'Gyarados (Calico Orange White Black)', 'BM3D_2234'),
('2235', '130', 'BM3D_2235', 'pixelmon:base:calico_white_orange:always', 'Gyarados (Calico White Orange)', 'BM3D_2235'),
('2236', '130', 'BM3D_2236', 'pixelmon:base:drowned:always', 'Gyarados (Drowned)', 'BM3D_2236'),
('2237', '130', 'BM3D_2237', 'pixelmon:base:gray_bubbles:always', 'Gyarados (Gray Bubbles)', 'BM3D_2237'),
('2238', '130', 'BM3D_2238', 'pixelmon:base:gray_diamonds:always', 'Gyarados (Gray Diamonds)', 'BM3D_2238'),
('2239', '130', 'BM3D_2239', 'pixelmon:base:gray_patches:always', 'Gyarados (Gray Patches)', 'BM3D_2239'),
('2240', '130', 'BM3D_2240', 'pixelmon:base:orange_dapples:always', 'Gyarados (Orange Dapples)', 'BM3D_2240'),
('2241', '130', 'BM3D_2241', 'pixelmon:base:orange_forehead:always', 'Gyarados (Orange Forehead)', 'BM3D_2241'),
('2242', '130', 'BM3D_2242', 'pixelmon:base:orange_mask:always', 'Gyarados (Orange Mask)', 'BM3D_2242'),
('2243', '130', 'BM3D_2243', 'pixelmon:base:orange_orca:always', 'Gyarados (Orange Orca)', 'BM3D_2243'),
('2244', '130', 'BM3D_2244', 'pixelmon:base:orange_twotone:always', 'Gyarados (Orange Twotone)', 'BM3D_2244'),
('2245', '130', 'BM3D_2245', 'pixelmon:base:pink_dapples:always', 'Gyarados (Pink Dapples)', 'BM3D_2245'),
('2246', '130', 'BM3D_2246', 'pixelmon:base:pink_orca:always', 'Gyarados (Pink Orca)', 'BM3D_2246'),
('2247', '130', 'BM3D_2247', 'pixelmon:base:pink_twotone:always', 'Gyarados (Pink Twotone)', 'BM3D_2247'),
('2248', '130', 'BM3D_2248', 'pixelmon:base:purple_bubbles:always', 'Gyarados (Purple Bubbles)', 'BM3D_2248'),
('2249', '130', 'BM3D_2249', 'pixelmon:base:purple_diamonds:always', 'Gyarados (Purple Diamonds)', 'BM3D_2249'),
('2250', '130', 'BM3D_2250', 'pixelmon:base:purple_patches:always', 'Gyarados (Purple Patches)', 'BM3D_2250'),
('2251', '130', 'BM3D_2251', 'pixelmon:base:skelly:always', 'Gyarados (Skelly)', 'BM3D_2251'),
('2252', '130', 'BM3D_2252', 'pixelmon:base:valencian:always', 'Gyarados (Valencian)', 'BM3D_2252'),
('2253', '130', 'BM3D_2253', 'pixelmon:base:violet_raindrops:always', 'Gyarados (Violet Raindrops)', 'BM3D_2253'),
('2254', '130', 'BM3D_2254', 'pixelmon:base:violet_saucy:always', 'Gyarados (Violet Saucy)', 'BM3D_2254'),
('2255', '130', 'BM3D_2255', 'pixelmon:base:zombie:always', 'Gyarados (Zombie)', 'BM3D_2255'),
('2256', '131', 'BM3D_2256', 'pixelmon:gmax:none:always', 'Lapras (Gmax)', 'BM3D_2256'),
('2258', '132', 'BM3D_2258', 'pixelmon:base:zombie:always', 'Ditto (Zombie)', 'BM3D_2258'),
('2259', '133', 'BM3D_2259', 'pixelmon:base:creator:always', 'Eevee (Creator)', 'BM3D_2259'),
('2260', '133', 'BM3D_2260', 'pixelmon:base:spirit:always', 'Eevee (Spirit)', 'BM3D_2260'),
('2261', '133', 'BM3D_2261', 'pixelmon:base:strike:always', 'Eevee (Strike)', 'BM3D_2261'),
('2262', '133', 'BM3D_2262', 'pixelmon:gmax:none:always', 'Eevee (Gmax)', 'BM3D_2262'),
('2264', '134', 'BM3D_2264', 'pixelmon:base:spirit:always', 'Vaporeon (Spirit)', 'BM3D_2264'),
('2265', '134', 'BM3D_2265', 'pixelmon:base:strike:always', 'Vaporeon (Strike)', 'BM3D_2265'),
('2266', '135', 'BM3D_2266', 'pixelmon:base:spirit:always', 'Jolteon (Spirit)', 'BM3D_2266'),
('2267', '135', 'BM3D_2267', 'pixelmon:base:strike:always', 'Jolteon (Strike)', 'BM3D_2267'),
('2268', '136', 'BM3D_2268', 'pixelmon:base:spirit:always', 'Flareon (Spirit)', 'BM3D_2268'),
('2269', '137', 'BM3D_2269', 'pixelmon:base:alter:always', 'Porygon (Alter)', 'BM3D_2269'),
('2270', '138', 'BM3D_2270', 'pixelmon:base:summer:always', 'Omanyte (Summer)', 'BM3D_2270'),
('2271', '139', 'BM3D_2271', 'pixelmon:base:drowned:always', 'Omastar (Drowned)', 'BM3D_2271'),
('2272', '143', 'BM3D_2272', 'pixelmon:base:christmas:always', 'Snorlax (Christmas)', 'BM3D_2272'),
('2273', '143', 'BM3D_2273', 'pixelmon:base:elf:always', 'Snorlax (Elf)', 'BM3D_2273'),
('2274', '143', 'BM3D_2274', 'pixelmon:base:snow:always', 'Snorlax (Snow)', 'BM3D_2274'),
('2275', '143', 'BM3D_2275', 'pixelmon:base:summer:always', 'Snorlax (Summer)', 'BM3D_2275'),
('2276', '143', 'BM3D_2276', 'pixelmon:gmax:christmas:always', 'Snorlax (Gmax, Christmas)', 'BM3D_2276'),
('2277', '143', 'BM3D_2277', 'pixelmon:gmax:elf:always', 'Snorlax (Gmax, Elf)', 'BM3D_2277'),
('2278', '143', 'BM3D_2278', 'pixelmon:gmax:none:always', 'Snorlax (Gmax)', 'BM3D_2278'),
('2280', '143', 'BM3D_2280', 'pixelmon:gmax:snow:always', 'Snorlax (Gmax, Snow)', 'BM3D_2280'),
('2281', '143', 'BM3D_2281', 'pixelmon:gmax:summer:always', 'Snorlax (Gmax, Summer)', 'BM3D_2281'),
('2282', '144', 'BM3D_2282', 'pixelmon:base:none:flying', 'Articuno (Flying)', 'BM3D_2282'),
('2284', '145', 'BM3D_2284', 'pixelmon:base:none:flying', 'Zapdos (Flying)', 'BM3D_2284'),
('2286', '145', 'BM3D_2286', 'pixelmon:galarian:none:always', 'Zapdos (Galarian)', 'BM3D_2286'),
('2288', '146', 'BM3D_2288', 'pixelmon:base:none:flying', 'Moltres (Flying)', 'BM3D_2288'),
('2289', '146', 'BM3D_2289', 'pixelmon:base:none:always', 'Moltres (State 1)', 'BM3D_2289'),
('2292', '146', 'BM3D_2292', 'pixelmon:galarian:none:always', 'Moltres (Galarian)', 'BM3D_2292'),
('2294', '147', 'BM3D_2294', 'pixelmon:base:christmas:always', 'Dratini (Christmas)', 'BM3D_2294'),
('2295', '147', 'BM3D_2295', 'pixelmon:base:elf:always', 'Dratini (Elf)', 'BM3D_2295'),
('2296', '148', 'BM3D_2296', 'pixelmon:base:christmas:always', 'Dragonair (Christmas)', 'BM3D_2296'),
('2297', '148', 'BM3D_2297', 'pixelmon:base:elf:always', 'Dragonair (Elf)', 'BM3D_2297'),
('2298', '149', 'BM3D_2298', 'pixelmon:base:ashen:always', 'Dragonite (Ashen)', 'BM3D_2298'),
('2299', '149', 'BM3D_2299', 'pixelmon:base:christmas:always', 'Dragonite (Christmas)', 'BM3D_2299'),
('2300', '149', 'BM3D_2300', 'pixelmon:base:elf:always', 'Dragonite (Elf)', 'BM3D_2300'),
('2301', '149', 'BM3D_2301', 'pixelmon:creator:none:always', 'Dragonite (Creator)', 'BM3D_2301'),
('2302', '150', 'BM3D_2302', 'pixelmon:base:online:always', 'Mewtwo (Online)', 'BM3D_2302'),
('2303', '151', 'BM3D_2303', 'pixelmon:base:christmas:always', 'Mew (Christmas)', 'BM3D_2303'),
('2304', '151', 'BM3D_2304', 'pixelmon:base:elf:always', 'Mew (Elf)', 'BM3D_2304'),
('2305', '154', 'BM3D_2305', 'pixelmon:base:zombie:always', 'Meganium (Zombie)', 'BM3D_2305'),
('2306', '157', 'BM3D_2306', 'pixelmon:base:zombie:always', 'Typhlosion (Zombie)', 'BM3D_2306'),
('2307', '160', 'BM3D_2307', 'pixelmon:base:zombie:always', 'Feraligatr (Zombie)', 'BM3D_2307'),
('2308', '161', 'BM3D_2308', 'pixelmon:base:online:always', 'Sentret (Online)', 'BM3D_2308'),
('2309', '164', 'BM3D_2309', 'pixelmon:base:none:flying', 'Noctowl (Flying)', 'BM3D_2309'),
('2311', '165', 'BM3D_2311', 'pixelmon:base:none:flying', 'Ledyba (Flying)', 'BM3D_2311'),
('2313', '166', 'BM3D_2313', 'pixelmon:base:none:flying', 'Ledian (Flying)', 'BM3D_2313'),
('2315', '169', 'BM3D_2315', 'pixelmon:base:strike:always', 'Crobat (Strike)', 'BM3D_2315'),
('2316', '172', 'BM3D_2316', 'pixelmon:base:christmas:always', 'Pichu (Christmas)', 'BM3D_2316'),
('2317', '172', 'BM3D_2317', 'pixelmon:base:elf:always', 'Pichu (Elf)', 'BM3D_2317'),
('2318', '172', 'BM3D_2318', 'pixelmon:spiky:none:always', 'Pichu (Spiky)', 'BM3D_2318'),
('2320', '175', 'BM3D_2320', 'pixelmon:base:valentine:always', 'Togepi (Valentine)', 'BM3D_2320'),
('2321', '176', 'BM3D_2321', 'pixelmon:base:valentine:flying', 'Togetic (Valentine, Flying)', 'BM3D_2321'),
('2322', '176', 'BM3D_2322', 'pixelmon:base:valentine:always', 'Togetic (Valentine, State 1)', 'BM3D_2322'),
('2323', '178', 'BM3D_2323', 'pixelmon:base:none:flying', 'Xatu (Flying)', 'BM3D_2323'),
('2325', '179', 'BM3D_2325', 'pixelmon:base:black:always', 'Mareep (Black)', 'BM3D_2325'),
('2326', '179', 'BM3D_2326', 'pixelmon:base:blue:always', 'Mareep (Blue)', 'BM3D_2326'),
('2327', '179', 'BM3D_2327', 'pixelmon:base:brown:always', 'Mareep (Brown)', 'BM3D_2327'),
('2328', '179', 'BM3D_2328', 'pixelmon:base:cyan:always', 'Mareep (Cyan)', 'BM3D_2328'),
('2329', '179', 'BM3D_2329', 'pixelmon:base:gray:always', 'Mareep (Gray)', 'BM3D_2329'),
('2330', '179', 'BM3D_2330', 'pixelmon:base:green:always', 'Mareep (Green)', 'BM3D_2330'),
('2331', '179', 'BM3D_2331', 'pixelmon:base:lightblue:always', 'Mareep (Lightblue)', 'BM3D_2331'),
('2332', '179', 'BM3D_2332', 'pixelmon:base:lightgray:always', 'Mareep (Lightgray)', 'BM3D_2332'),
('2333', '179', 'BM3D_2333', 'pixelmon:base:lime:always', 'Mareep (Lime)', 'BM3D_2333'),
('2334', '179', 'BM3D_2334', 'pixelmon:base:magenta:always', 'Mareep (Magenta)', 'BM3D_2334'),
('2335', '179', 'BM3D_2335', 'pixelmon:base:orange:always', 'Mareep (Orange)', 'BM3D_2335'),
('2336', '179', 'BM3D_2336', 'pixelmon:base:pink:always', 'Mareep (Pink)', 'BM3D_2336'),
('2337', '179', 'BM3D_2337', 'pixelmon:base:purple:always', 'Mareep (Purple)', 'BM3D_2337'),
('2338', '179', 'BM3D_2338', 'pixelmon:base:red:always', 'Mareep (Red)', 'BM3D_2338'),
('2339', '179', 'BM3D_2339', 'pixelmon:base:yellow:always', 'Mareep (Yellow)', 'BM3D_2339'),
('2340', '179', 'BM3D_2340', 'pixelmon:shorn:black:always', 'Mareep (Shorn, Black)', 'BM3D_2340'),
('2341', '179', 'BM3D_2341', 'pixelmon:shorn:blue:always', 'Mareep (Shorn, Blue)', 'BM3D_2341'),
('2342', '179', 'BM3D_2342', 'pixelmon:shorn:brown:always', 'Mareep (Shorn, Brown)', 'BM3D_2342'),
('2343', '179', 'BM3D_2343', 'pixelmon:shorn:cyan:always', 'Mareep (Shorn, Cyan)', 'BM3D_2343'),
('2344', '179', 'BM3D_2344', 'pixelmon:shorn:gray:always', 'Mareep (Shorn, Gray)', 'BM3D_2344'),
('2345', '179', 'BM3D_2345', 'pixelmon:shorn:green:always', 'Mareep (Shorn, Green)', 'BM3D_2345'),
('2346', '179', 'BM3D_2346', 'pixelmon:shorn:lightblue:always', 'Mareep (Shorn, Lightblue)', 'BM3D_2346'),
('2347', '179', 'BM3D_2347', 'pixelmon:shorn:lightgray:always', 'Mareep (Shorn, Lightgray)', 'BM3D_2347'),
('2348', '179', 'BM3D_2348', 'pixelmon:shorn:lime:always', 'Mareep (Shorn, Lime)', 'BM3D_2348'),
('2349', '179', 'BM3D_2349', 'pixelmon:shorn:magenta:always', 'Mareep (Shorn, Magenta)', 'BM3D_2349'),
('2350', '179', 'BM3D_2350', 'pixelmon:shorn:none:always', 'Mareep (Shorn)', 'BM3D_2350'),
('2351', '179', 'BM3D_2351', 'pixelmon:shorn:orange:always', 'Mareep (Shorn, Orange)', 'BM3D_2351'),
('2352', '179', 'BM3D_2352', 'pixelmon:shorn:pink:always', 'Mareep (Shorn, Pink)', 'BM3D_2352'),
('2353', '179', 'BM3D_2353', 'pixelmon:shorn:purple:always', 'Mareep (Shorn, Purple)', 'BM3D_2353'),
('2354', '179', 'BM3D_2354', 'pixelmon:shorn:red:always', 'Mareep (Shorn, Red)', 'BM3D_2354'),
('2356', '179', 'BM3D_2356', 'pixelmon:shorn:yellow:always', 'Mareep (Shorn, Yellow)', 'BM3D_2356'),
('2357', '182', 'BM3D_2357', 'pixelmon:base:pink:always', 'Bellossom (Pink)', 'BM3D_2357'),
('2358', '182', 'BM3D_2358', 'pixelmon:base:valencian:always', 'Bellossom (Valencian)', 'BM3D_2358'),
('2359', '183', 'BM3D_2359', 'pixelmon:base:alter:always', 'Marill (Alter)', 'BM3D_2359'),
('2360', '184', 'BM3D_2360', 'pixelmon:base:alter:always', 'Azumarill (Alter)', 'BM3D_2360'),
('2361', '186', 'BM3D_2361', 'pixelmon:base:valencian:always', 'Politoed (Valencian)', 'BM3D_2361'),
('2362', '196', 'BM3D_2362', 'pixelmon:base:spirit:always', 'Espeon (Spirit)', 'BM3D_2362'),
('2363', '196', 'BM3D_2363', 'pixelmon:base:strike:always', 'Espeon (Strike)', 'BM3D_2363'),
('2364', '197', 'BM3D_2364', 'pixelmon:base:ashen:always', 'Umbreon (Ashen)', 'BM3D_2364'),
('2365', '197', 'BM3D_2365', 'pixelmon:base:spirit:always', 'Umbreon (Spirit)', 'BM3D_2365'),
('2366', '197', 'BM3D_2366', 'pixelmon:base:strike:always', 'Umbreon (Strike)', 'BM3D_2366'),
('2367', '198', 'BM3D_2367', 'pixelmon:base:none:flying', 'Murkrow (Flying)', 'BM3D_2367'),
('2369', '200', 'BM3D_2369', 'pixelmon:base:pink:always', 'Misdreavus (Pink)', 'BM3D_2369'),
('2370', '200', 'BM3D_2370', 'pixelmon:base:witch:always', 'Misdreavus (Witch)', 'BM3D_2370'),
('2371', '202', 'BM3D_2371', 'pixelmon:base:online:always', 'Wobbuffet (Online, Female)', 'BM3D_2371'),
('2372', '202', 'BM3D_2372', 'pixelmon:base:online:always', 'Wobbuffet (Online, Male)', 'BM3D_2372'),
('2373', '208', 'BM3D_2373', 'pixelmon:base:crystal:always', 'Steelix (Crystal)', 'BM3D_2373'),
('2374', '208', 'BM3D_2374', 'pixelmon:mega:crystal:always', 'Steelix (Mega, Crystal)', 'BM3D_2374'),
('2375', '211', 'BM3D_2375', 'pixelmon:base:drowned:always', 'Qwilfish (Drowned)', 'BM3D_2375'),
('2376', '215', 'BM3D_2376', 'pixelmon:base:strike:always', 'Sneasel (Strike)', 'BM3D_2376'),
('2377', '218', 'BM3D_2377', 'pixelmon:base:calcium_carbonate:always', 'Slugma (Calcium Carbonate)', 'BM3D_2377'),
('2378', '218', 'BM3D_2378', 'pixelmon:base:copper_sulfate:always', 'Slugma (Copper Sulfate)', 'BM3D_2378'),
('2379', '218', 'BM3D_2379', 'pixelmon:base:cupric_chloride:always', 'Slugma (Cupric Chloride)', 'BM3D_2379'),
('2380', '218', 'BM3D_2380', 'pixelmon:base:lithium_chloride:always', 'Slugma (Lithium Chloride)', 'BM3D_2380'),
('2381', '218', 'BM3D_2381', 'pixelmon:base:magnesium_sulfide:always', 'Slugma (Magnesium Sulfide)', 'BM3D_2381'),
('2382', '218', 'BM3D_2382', 'pixelmon:base:manganese_chloride:always', 'Slugma (Manganese Chloride)', 'BM3D_2382'),
('2383', '218', 'BM3D_2383', 'pixelmon:base:potassium_chloride:always', 'Slugma (Potassium Chloride)', 'BM3D_2383'),
('2384', '218', 'BM3D_2384', 'pixelmon:base:sodium_carbonate:always', 'Slugma (Sodium Carbonate)', 'BM3D_2384'),
('2385', '223', 'BM3D_2385', 'pixelmon:base:drowned:always', 'Remoraid (Drowned)', 'BM3D_2385'),
('2386', '224', 'BM3D_2386', 'pixelmon:base:drowned:always', 'Octillery (Drowned)', 'BM3D_2386'),
('2387', '225', 'BM3D_2387', 'pixelmon:base:christmas:always', 'Delibird (Christmas)', 'BM3D_2387'),
('2388', '227', 'BM3D_2388', 'pixelmon:base:rainbow:flying', 'Skarmory (Rainbow, Flying)', 'BM3D_2388'),
('2389', '227', 'BM3D_2389', 'pixelmon:base:rainbow:always', 'Skarmory (Rainbow, State 1)', 'BM3D_2389'),
('2390', '229', 'BM3D_2390', 'pixelmon:base:ashen:always', 'Houndoom (Ashen)', 'BM3D_2390'),
('2391', '230', 'BM3D_2391', 'pixelmon:base:drowned:always', 'Kingdra (Drowned)', 'BM3D_2391'),
('2392', '233', 'BM3D_2392', 'pixelmon:base:alter:always', 'Porygon2 (Alter)', 'BM3D_2392'),
('2393', '233', 'BM3D_2393', 'pixelmon:base:spirit:always', 'Porygon2 (Spirit)', 'BM3D_2393'),
('2394', '242', 'BM3D_2394', 'pixelmon:base:valencian:always', 'Blissey (Valencian)', 'BM3D_2394'),
('2395', '245', 'BM3D_2395', 'pixelmon:base:spirit:always', 'Suicune (Spirit)', 'BM3D_2395'),
('2396', '249', 'BM3D_2396', 'pixelmon:base:drowned:flying', 'Lugia (Drowned, Flying)', 'BM3D_2396'),
('2397', '249', 'BM3D_2397', 'pixelmon:base:drowned:always', 'Lugia (Drowned, State 1)', 'BM3D_2397'),
('2398', '249', 'BM3D_2398', 'pixelmon:base:none:flying', 'Lugia (Flying)', 'BM3D_2398'),
('2399', '249', 'BM3D_2399', 'pixelmon:base:online:flying', 'Lugia (Online, Flying)', 'BM3D_2399'),
('2400', '249', 'BM3D_2400', 'pixelmon:base:online:always', 'Lugia (Online, State 1)', 'BM3D_2400'),
('2402', '250', 'BM3D_2402', 'pixelmon:base:none:flying', 'Ho-Oh (Flying)', 'BM3D_2402'),
('2403', '250', 'BM3D_2403', 'pixelmon:base:online:flying', 'Ho-Oh (Online, Flying)', 'BM3D_2403'),
('2404', '250', 'BM3D_2404', 'pixelmon:base:online:always', 'Ho-Oh (Online, State 1)', 'BM3D_2404'),
('2405', '250', 'BM3D_2405', 'pixelmon:base:rainbow:flying', 'Ho-Oh (Rainbow, Flying)', 'BM3D_2405'),
('2406', '250', 'BM3D_2406', 'pixelmon:base:rainbow:always', 'Ho-Oh (Rainbow, State 1)', 'BM3D_2406'),
('2408', '251', 'BM3D_2408', 'pixelmon:base:alien:always', 'Celebi (Alien)', 'BM3D_2408'),
('2409', '251', 'BM3D_2409', 'pixelmon:base:valentine:always', 'Celebi (Valentine)', 'BM3D_2409'),
('2410', '254', 'BM3D_2410', 'pixelmon:base:zombie:always', 'Sceptile (Zombie)', 'BM3D_2410'),
('2411', '257', 'BM3D_2411', 'pixelmon:base:zombie:always', 'Blaziken (Zombie)', 'BM3D_2411'),
('2412', '260', 'BM3D_2412', 'pixelmon:base:zombie:always', 'Swampert (Zombie)', 'BM3D_2412'),
('2413', '267', 'BM3D_2413', 'pixelmon:base:rainbow:always', 'Beautifly (Rainbow)', 'BM3D_2413'),
('2414', '269', 'BM3D_2414', 'pixelmon:base:ashen:always', 'Dustox (Ashen)', 'BM3D_2414'),
('2415', '269', 'BM3D_2415', 'pixelmon:base:rainbow:always', 'Dustox (Rainbow)', 'BM3D_2415'),
('2416', '276', 'BM3D_2416', 'pixelmon:base:none:flying', 'Taillow (Flying)', 'BM3D_2416'),
('2418', '277', 'BM3D_2418', 'pixelmon:base:none:flying', 'Swellow (Flying)', 'BM3D_2418'),
('2420', '280', 'BM3D_2420', 'pixelmon:base:strike:always', 'Ralts (Strike)', 'BM3D_2420'),
('2421', '281', 'BM3D_2421', 'pixelmon:base:strike:always', 'Kirlia (Strike)', 'BM3D_2421'),
('2422', '282', 'BM3D_2422', 'pixelmon:base:strike:always', 'Gardevoir (Strike)', 'BM3D_2422'),
('2423', '282', 'BM3D_2423', 'pixelmon:base:valentine:always', 'Gardevoir (Valentine)', 'BM3D_2423'),
('2424', '285', 'BM3D_2424', 'pixelmon:base:spirit:always', 'Shroomish (Spirit)', 'BM3D_2424'),
('2425', '286', 'BM3D_2425', 'pixelmon:base:spirit:always', 'Breloom (Spirit)', 'BM3D_2425'),
('2426', '292', 'BM3D_2426', 'pixelmon:base:alter:always', 'Shedinja (Alter)', 'BM3D_2426'),
('2427', '302', 'BM3D_2427', 'pixelmon:base:drowned:always', 'Sableye (Drowned)', 'BM3D_2427'),
('2428', '302', 'BM3D_2428', 'pixelmon:base:zombie:always', 'Sableye (Zombie)', 'BM3D_2428'),
('2429', '327', 'BM3D_2429', 'pixelmon:base:valentine:always', 'Spinda (Valentine)', 'BM3D_2429'),
('2430', '330', 'BM3D_2430', 'pixelmon:base:drowned:flying', 'Flygon (Drowned, Flying)', 'BM3D_2430'),
('2431', '330', 'BM3D_2431', 'pixelmon:base:drowned:always', 'Flygon (Drowned, State 1)', 'BM3D_2431'),
('2432', '330', 'BM3D_2432', 'pixelmon:base:none:flying', 'Flygon (Flying)', 'BM3D_2432'),
('2434', '333', 'BM3D_2434', 'pixelmon:base:valentine:always', 'Swablu (Valentine)', 'BM3D_2434'),
('2435', '334', 'BM3D_2435', 'pixelmon:base:valentine:always', 'Altaria (Valentine)', 'BM3D_2435'),
('2436', '337', 'BM3D_2436', 'pixelmon:crescent:none:always', 'Lunatone (Crescent)', 'BM3D_2436'),
('2438', '337', 'BM3D_2438', 'pixelmon:full:none:always', 'Lunatone (Full)', 'BM3D_2438'),
('2440', '337', 'BM3D_2440', 'pixelmon:new_moon:none:always', 'Lunatone (New Moon)', 'BM3D_2440'),
('2442', '337', 'BM3D_2442', 'pixelmon:quarter:none:always', 'Lunatone (Quarter)', 'BM3D_2442'),
('2444', '342', 'BM3D_2444', 'pixelmon:base:rainbow:always', 'Crawdaunt (Rainbow)', 'BM3D_2444'),
('2445', '343', 'BM3D_2445', 'pixelmon:base:alter:always', 'Baltoy (Alter)', 'BM3D_2445'),
('2446', '344', 'BM3D_2446', 'pixelmon:base:alter:always', 'Claydol (Alter)', 'BM3D_2446'),
('2447', '344', 'BM3D_2447', 'pixelmon:base:drowned:always', 'Claydol (Drowned)', 'BM3D_2447'),
('2448', '349', 'BM3D_2448', 'pixelmon:base:karp:always', 'Feebas (Karp)', 'BM3D_2448'),
('2449', '349', 'BM3D_2449', 'pixelmon:base:rainbow:always', 'Feebas (Rainbow)', 'BM3D_2449'),
('2450', '350', 'BM3D_2450', 'pixelmon:base:rainbow:always', 'Milotic (Rainbow)', 'BM3D_2450'),
('2451', '350', 'BM3D_2451', 'pixelmon:base:spirit:always', 'Milotic (Spirit)', 'BM3D_2451'),
('2452', '351', 'BM3D_2452', 'pixelmon:base:christmas:always', 'Castform (Christmas)', 'BM3D_2452'),
('2453', '351', 'BM3D_2453', 'pixelmon:rain:christmas:always', 'Castform (Rain, Christmas)', 'BM3D_2453'),
('2456', '352', 'BM3D_2456', 'pixelmon:base:alter:always', 'Kecleon (Alter)', 'BM3D_2456'),
('2457', '352', 'BM3D_2457', 'pixelmon:base:rainbow:always', 'Kecleon (Rainbow)', 'BM3D_2457'),
('2458', '353', 'BM3D_2458', 'pixelmon:base:witch:always', 'Shuppet (Witch)', 'BM3D_2458'),
('2459', '354', 'BM3D_2459', 'pixelmon:base:witch:always', 'Banette (Witch)', 'BM3D_2459'),
('2460', '359', 'BM3D_2460', 'pixelmon:base:valentine:always', 'Absol (Valentine)', 'BM3D_2460'),
('2461', '363', 'BM3D_2461', 'pixelmon:base:duskball:always', 'Spheal (Duskball)', 'BM3D_2461'),
('2462', '363', 'BM3D_2462', 'pixelmon:base:friendball:always', 'Spheal (Friendball)', 'BM3D_2462'),
('2463', '363', 'BM3D_2463', 'pixelmon:base:gsball:always', 'Spheal (Gsball)', 'BM3D_2463'),
('2464', '363', 'BM3D_2464', 'pixelmon:base:heavyball:always', 'Spheal (Heavyball)', 'BM3D_2464'),
('2465', '363', 'BM3D_2465', 'pixelmon:base:loveball:always', 'Spheal (Loveball)', 'BM3D_2465'),
('2466', '363', 'BM3D_2466', 'pixelmon:base:masterball:always', 'Spheal (Masterball)', 'BM3D_2466'),
('2467', '363', 'BM3D_2467', 'pixelmon:base:moonball:always', 'Spheal (Moonball)', 'BM3D_2467'),
('2468', '363', 'BM3D_2468', 'pixelmon:base:online:always', 'Spheal (Online)', 'BM3D_2468'),
('2469', '363', 'BM3D_2469', 'pixelmon:base:pokeball:always', 'Spheal (Pokeball)', 'BM3D_2469'),
('2470', '363', 'BM3D_2470', 'pixelmon:base:premierball:always', 'Spheal (Premierball)', 'BM3D_2470'),
('2471', '369', 'BM3D_2471', 'pixelmon:base:drowned:always', 'Relicanth (Drowned)', 'BM3D_2471'),
('2472', '371', 'BM3D_2472', 'pixelmon:base:alter:always', 'Bagon (Alter)', 'BM3D_2472'),
('2473', '372', 'BM3D_2473', 'pixelmon:base:alter:always', 'Shelgon (Alter)', 'BM3D_2473'),
('2474', '373', 'BM3D_2474', 'pixelmon:base:alter:always', 'Salamence (Alter)', 'BM3D_2474'),
('2475', '376', 'BM3D_2475', 'pixelmon:base:none:flying', 'Metagross (Flying)', 'BM3D_2475'),
('2477', '378', 'BM3D_2477', 'pixelmon:base:none:always', 'Regice', 'BM3D_2477'),
('2479', '383', 'BM3D_2479', 'pixelmon:base:meta:always', 'Groudon (Meta)', 'BM3D_2479'),
('2480', '384', 'BM3D_2480', 'pixelmon:base:alter:always', 'Rayquaza (Alter)', 'BM3D_2480'),
('2481', '386', 'BM3D_2481', 'pixelmon:sus:none:always', 'Deoxys (Sus)', 'BM3D_2481'),
('2483', '389', 'BM3D_2483', 'pixelmon:base:zombie:always', 'Torterra (Zombie)', 'BM3D_2483'),
('2484', '392', 'BM3D_2484', 'pixelmon:base:rainbow:always', 'Infernape (Rainbow)', 'BM3D_2484'),
('2485', '392', 'BM3D_2485', 'pixelmon:base:zombie:always', 'Infernape (Zombie)', 'BM3D_2485'),
('2486', '395', 'BM3D_2486', 'pixelmon:base:zombie:always', 'Empoleon (Zombie)', 'BM3D_2486'),
('2487', '396', 'BM3D_2487', 'pixelmon:base:none:flying', 'Starly (Flying)', 'BM3D_2487'),
('2489', '397', 'BM3D_2489', 'pixelmon:base:none:flying', 'Staravia (Flying)', 'BM3D_2489'),
('2491', '398', 'BM3D_2491', 'pixelmon:base:none:flying', 'Staraptor (Flying)', 'BM3D_2491'),
('2493', '399', 'BM3D_2493', 'pixelmon:sirdoofusiii:none:always', 'Bidoof (Sirdoofusiii)', 'BM3D_2493'),
('2495', '407', 'BM3D_2495', 'pixelmon:base:ashen:always', 'Roserade (Ashen)', 'BM3D_2495'),
('2496', '414', 'BM3D_2496', 'pixelmon:base:online:always', 'Mothim (Online)', 'BM3D_2496'),
('2497', '422', 'BM3D_2497', 'pixelmon:east:apricot_saucy:always', 'Shellos (East, Apricot Saucy)', 'BM3D_2497'),
('2498', '422', 'BM3D_2498', 'pixelmon:east:golde:always', 'Shellos (East, Golde)', 'BM3D_2498'),
('2499', '422', 'BM3D_2499', 'pixelmon:east:gray_bubbles:always', 'Shellos (East, Gray Bubbles)', 'BM3D_2499'),
('2500', '422', 'BM3D_2500', 'pixelmon:east:moons:always', 'Shellos (East, Moons)', 'BM3D_2500'),
('2501', '422', 'BM3D_2501', 'pixelmon:east:purple_bubbles:always', 'Shellos (East, Purple Bubbles)', 'BM3D_2501'),
('2502', '422', 'BM3D_2502', 'pixelmon:east:violet_saucy:always', 'Shellos (East, Violet Saucy)', 'BM3D_2502'),
('2503', '422', 'BM3D_2503', 'pixelmon:west:blue_stripes:always', 'Shellos (West, Blue Stripes)', 'BM3D_2503'),
('2504', '422', 'BM3D_2504', 'pixelmon:west:brown_stripes:always', 'Shellos (West, Brown Stripes)', 'BM3D_2504'),
('2505', '422', 'BM3D_2505', 'pixelmon:west:goldw:always', 'Shellos (West, Goldw)', 'BM3D_2505'),
('2506', '422', 'BM3D_2506', 'pixelmon:west:gray_diamonds:always', 'Shellos (West, Gray Diamonds)', 'BM3D_2506'),
('2507', '422', 'BM3D_2507', 'pixelmon:west:purple_diamonds:always', 'Shellos (West, Purple Diamonds)', 'BM3D_2507'),
('2508', '422', 'BM3D_2508', 'pixelmon:west:sun:always', 'Shellos (West, Sun)', 'BM3D_2508'),
('2509', '423', 'BM3D_2509', 'pixelmon:east:apricot_saucy:always', 'Gastrodon (East, Apricot Saucy)', 'BM3D_2509'),
('2510', '423', 'BM3D_2510', 'pixelmon:east:golde:always', 'Gastrodon (East, Golde)', 'BM3D_2510'),
('2511', '423', 'BM3D_2511', 'pixelmon:east:gray_bubbles:always', 'Gastrodon (East, Gray Bubbles)', 'BM3D_2511'),
('2512', '423', 'BM3D_2512', 'pixelmon:east:moons:always', 'Gastrodon (East, Moons)', 'BM3D_2512'),
('2513', '423', 'BM3D_2513', 'pixelmon:east:purple_bubbles:always', 'Gastrodon (East, Purple Bubbles)', 'BM3D_2513'),
('2514', '423', 'BM3D_2514', 'pixelmon:east:violet_saucy:always', 'Gastrodon (East, Violet Saucy)', 'BM3D_2514'),
('2515', '423', 'BM3D_2515', 'pixelmon:west:blue_stripes:always', 'Gastrodon (West, Blue Stripes)', 'BM3D_2515'),
('2516', '423', 'BM3D_2516', 'pixelmon:west:brown_stripes:always', 'Gastrodon (West, Brown Stripes)', 'BM3D_2516'),
('2517', '423', 'BM3D_2517', 'pixelmon:west:goldw:always', 'Gastrodon (West, Goldw)', 'BM3D_2517'),
('2518', '423', 'BM3D_2518', 'pixelmon:west:gray_diamonds:always', 'Gastrodon (West, Gray Diamonds)', 'BM3D_2518'),
('2519', '423', 'BM3D_2519', 'pixelmon:west:purple_diamonds:always', 'Gastrodon (West, Purple Diamonds)', 'BM3D_2519'),
('2520', '423', 'BM3D_2520', 'pixelmon:west:sun:always', 'Gastrodon (West, Sun)', 'BM3D_2520'),
('2521', '425', 'BM3D_2521', 'pixelmon:base:valentine:always', 'Drifloon (Valentine)', 'BM3D_2521'),
('2522', '426', 'BM3D_2522', 'pixelmon:base:valentine:flying', 'Drifblim (Valentine, Flying)', 'BM3D_2522'),
('2523', '426', 'BM3D_2523', 'pixelmon:base:valentine:always', 'Drifblim (Valentine, State 1)', 'BM3D_2523'),
('2524', '428', 'BM3D_2524', 'pixelmon:base:summer:always', 'Lopunny (Summer)', 'BM3D_2524'),
('2525', '429', 'BM3D_2525', 'pixelmon:base:pink:always', 'Mismagius (Pink)', 'BM3D_2525'),
('2526', '429', 'BM3D_2526', 'pixelmon:base:witch:always', 'Mismagius (Witch)', 'BM3D_2526'),
('2527', '430', 'BM3D_2527', 'pixelmon:base:none:flying', 'Honchkrow (Flying)', 'BM3D_2527'),
('2529', '440', 'BM3D_2529', 'pixelmon:base:valencian:always', 'Happiny (Valencian)', 'BM3D_2529'),
('2530', '441', 'BM3D_2530', 'pixelmon:base:none:flying', 'Chatot (Flying)', 'BM3D_2530'),
('2534', '446', 'BM3D_2534', 'pixelmon:base:christmas:always', 'Munchlax (Christmas)', 'BM3D_2534'),
('2535', '446', 'BM3D_2535', 'pixelmon:base:elf:always', 'Munchlax (Elf)', 'BM3D_2535'),
('2536', '448', 'BM3D_2536', 'pixelmon:base:online:always', 'Lucario (Online)', 'BM3D_2536'),
('2537', '456', 'BM3D_2537', 'pixelmon:base:drowned:always', 'Finneon (Drowned)', 'BM3D_2537'),
('2538', '457', 'BM3D_2538', 'pixelmon:base:drowned:always', 'Lumineon (Drowned)', 'BM3D_2538'),
('2539', '459', 'BM3D_2539', 'pixelmon:base:christmas:always', 'Snover (Christmas)', 'BM3D_2539'),
('2540', '460', 'BM3D_2540', 'pixelmon:base:christmas:always', 'Abomasnow (Christmas)', 'BM3D_2540'),
('2541', '461', 'BM3D_2541', 'pixelmon:base:rainbow:always', 'Weavile (Rainbow)', 'BM3D_2541'),
('2542', '461', 'BM3D_2542', 'pixelmon:base:strike:always', 'Weavile (Strike)', 'BM3D_2542'),
('2543', '464', 'BM3D_2543', 'pixelmon:base:pink:always', 'Rhyperior (Pink)', 'BM3D_2543'),
('2544', '466', 'BM3D_2544', 'pixelmon:base:strike:always', 'Electivire (Strike)', 'BM3D_2544'),
('2545', '468', 'BM3D_2545', 'pixelmon:base:valentine:flying', 'Togekiss (Valentine, Flying)', 'BM3D_2545'),
('2546', '468', 'BM3D_2546', 'pixelmon:base:valentine:always', 'Togekiss (Valentine, State 1)', 'BM3D_2546'),
('2547', '470', 'BM3D_2547', 'pixelmon:base:spirit:always', 'Leafeon (Spirit)', 'BM3D_2547'),
('2548', '470', 'BM3D_2548', 'pixelmon:base:strike:always', 'Leafeon (Strike)', 'BM3D_2548'),
('2549', '471', 'BM3D_2549', 'pixelmon:base:spirit:always', 'Glaceon (Spirit)', 'BM3D_2549'),
('2550', '474', 'BM3D_2550', 'pixelmon:base:alter:always', 'Porygon-Z (Alter)', 'BM3D_2550'),
('2551', '475', 'BM3D_2551', 'pixelmon:base:strike:always', 'Gallade (Strike)', 'BM3D_2551'),
('2554', '488', 'BM3D_2554', 'pixelmon:base:rainbow:always', 'Cresselia (Rainbow)', 'BM3D_2554'),
('2555', '488', 'BM3D_2555', 'pixelmon:base:spirit:always', 'Cresselia (Spirit)', 'BM3D_2555'),
('2556', '492', 'BM3D_2556', 'pixelmon:land:christmas:always', 'Shaymin (Land, Christmas)', 'BM3D_2556'),
('2557', '492', 'BM3D_2557', 'pixelmon:sky:christmas:always', 'Shaymin (Sky, Christmas)', 'BM3D_2557'),
('2558', '497', 'BM3D_2558', 'pixelmon:base:zombie:always', 'Serperior (Zombie)', 'BM3D_2558'),
('2559', '500', 'BM3D_2559', 'pixelmon:base:zombie:always', 'Emboar (Zombie)', 'BM3D_2559'),
('2560', '503', 'BM3D_2560', 'pixelmon:base:zombie:always', 'Samurott (Zombie)', 'BM3D_2560'),
('2561', '522', 'BM3D_2561', 'pixelmon:base:none:always', 'Blitzle', 'BM3D_2561'),
('2563', '523', 'BM3D_2563', 'pixelmon:base:none:always', 'Zebstrika', 'BM3D_2563'),
('2569', '551', 'BM3D_2569', 'pixelmon:base:blocky:always', 'Sandile (Blocky)', 'BM3D_2569'),
('2570', '569', 'BM3D_2570', 'pixelmon:gmax:none:always', 'Garbodor (Gmax)', 'BM3D_2570'),
('2572', '570', 'BM3D_2572', 'pixelmon:base:alter:always', 'Zorua (Alter)', 'BM3D_2572'),
('2573', '570', 'BM3D_2573', 'pixelmon:hisuian:witch:always', 'Zorua (Hisuian, Witch)', 'BM3D_2573'),
('2574', '571', 'BM3D_2574', 'pixelmon:base:alter:always', 'Zoroark (Alter)', 'BM3D_2574'),
('2575', '571', 'BM3D_2575', 'pixelmon:hisuian:witch:always', 'Zoroark (Hisuian, Witch)', 'BM3D_2575'),
('2576', '587', 'BM3D_2576', 'pixelmon:base:valentine:always', 'Emolga (Valentine)', 'BM3D_2576'),
('2577', '591', 'BM3D_2577', 'pixelmon:base:black:always', 'Amoonguss (Black)', 'BM3D_2577'),
('2578', '591', 'BM3D_2578', 'pixelmon:base:brown:always', 'Amoonguss (Brown)', 'BM3D_2578'),
('2579', '591', 'BM3D_2579', 'pixelmon:base:cyan:always', 'Amoonguss (Cyan)', 'BM3D_2579'),
('2580', '591', 'BM3D_2580', 'pixelmon:base:dark_blue:always', 'Amoonguss (Dark Blue)', 'BM3D_2580'),
('2581', '591', 'BM3D_2581', 'pixelmon:base:dark_green:always', 'Amoonguss (Dark Green)', 'BM3D_2581'),
('2582', '591', 'BM3D_2582', 'pixelmon:base:dark_pink:always', 'Amoonguss (Dark Pink)', 'BM3D_2582'),
('2583', '591', 'BM3D_2583', 'pixelmon:base:dark_red:always', 'Amoonguss (Dark Red)', 'BM3D_2583'),
('2584', '591', 'BM3D_2584', 'pixelmon:base:forte_green:always', 'Amoonguss (Forte Green)', 'BM3D_2584'),
('2585', '591', 'BM3D_2585', 'pixelmon:base:grey:always', 'Amoonguss (Grey)', 'BM3D_2585'),
('2586', '591', 'BM3D_2586', 'pixelmon:base:light_brown:always', 'Amoonguss (Light Brown)', 'BM3D_2586'),
('2587', '591', 'BM3D_2587', 'pixelmon:base:light_pink:always', 'Amoonguss (Light Pink)', 'BM3D_2587'),
('2588', '591', 'BM3D_2588', 'pixelmon:base:light_yellow:always', 'Amoonguss (Light Yellow)', 'BM3D_2588'),
('2589', '591', 'BM3D_2589', 'pixelmon:base:lime:always', 'Amoonguss (Lime)', 'BM3D_2589'),
('2590', '591', 'BM3D_2590', 'pixelmon:base:olive:always', 'Amoonguss (Olive)', 'BM3D_2590'),
('2591', '591', 'BM3D_2591', 'pixelmon:base:orange:always', 'Amoonguss (Orange)', 'BM3D_2591'),
('2592', '591', 'BM3D_2592', 'pixelmon:base:pink:always', 'Amoonguss (Pink)', 'BM3D_2592'),
('2593', '591', 'BM3D_2593', 'pixelmon:base:purple:always', 'Amoonguss (Purple)', 'BM3D_2593'),
('2594', '591', 'BM3D_2594', 'pixelmon:base:red:always', 'Amoonguss (Red)', 'BM3D_2594'),
('2595', '591', 'BM3D_2595', 'pixelmon:base:white:always', 'Amoonguss (White)', 'BM3D_2595'),
('2596', '591', 'BM3D_2596', 'pixelmon:base:yellow:always', 'Amoonguss (Yellow)', 'BM3D_2596'),
('2601', '609', 'BM3D_2601', 'pixelmon:base:rainbow:always', 'Chandelure (Rainbow)', 'BM3D_2601'),
('2602', '609', 'BM3D_2602', 'pixelmon:mega:rainbow:always', 'Chandelure (Mega, Rainbow)', 'BM3D_2602'),
('2603', '615', 'BM3D_2603', 'pixelmon:base:christmas:always', 'Cryogonal (Christmas)', 'BM3D_2603'),
('2604', '623', 'BM3D_2604', 'pixelmon:base:none:flying', 'Golurk (Flying)', 'BM3D_2604'),
('2606', '627', 'BM3D_2606', 'pixelmon:base:none:flying', 'Rufflet (Flying)', 'BM3D_2606'),
('2608', '628', 'BM3D_2608', 'pixelmon:base:none:flying', 'Braviary (Flying)', 'BM3D_2608'),
('2610', '628', 'BM3D_2610', 'pixelmon:hisuian:none:flying', 'Braviary (Hisuian, Flying)', 'BM3D_2610'),
('2611', '628', 'BM3D_2611', 'pixelmon:hisuian:none:always', 'Braviary (Hisuian, State 1)', 'BM3D_2611'),
('2614', '635', 'BM3D_2614', 'pixelmon:base:ashen:flying', 'Hydreigon (Ashen, Flying)', 'BM3D_2614'),
('2615', '635', 'BM3D_2615', 'pixelmon:base:ashen:always', 'Hydreigon (Ashen, State 1)', 'BM3D_2615'),
('2616', '637', 'BM3D_2616', 'pixelmon:base:alter:flying', 'Volcarona (Alter, Flying)', 'BM3D_2616'),
('2617', '637', 'BM3D_2617', 'pixelmon:base:alter:always', 'Volcarona (Alter, State 1)', 'BM3D_2617'),
('2618', '652', 'BM3D_2618', 'pixelmon:base:zombie:always', 'Chesnaught (Zombie)', 'BM3D_2618'),
('2619', '655', 'BM3D_2619', 'pixelmon:base:zombie:always', 'Delphox (Zombie)', 'BM3D_2619'),
('2620', '656', 'BM3D_2620', 'pixelmon:base:alter:always', 'Froakie (Alter)', 'BM3D_2620'),
('2621', '657', 'BM3D_2621', 'pixelmon:base:alter:always', 'Frogadier (Alter)', 'BM3D_2621'),
('2622', '658', 'BM3D_2622', 'pixelmon:ash:alter:always', 'Greninja (Ash, Alter)', 'BM3D_2622'),
('2623', '658', 'BM3D_2623', 'pixelmon:ash:zombie:always', 'Greninja (Ash, Zombie)', 'BM3D_2623'),
('2624', '658', 'BM3D_2624', 'pixelmon:base:alter:always', 'Greninja (Alter)', 'BM3D_2624'),
('2625', '658', 'BM3D_2625', 'pixelmon:base:online:always', 'Greninja (Online)', 'BM3D_2625'),
('2626', '658', 'BM3D_2626', 'pixelmon:base:zombie:always', 'Greninja (Zombie)', 'BM3D_2626'),
('2627', '663', 'BM3D_2627', 'pixelmon:base:ashen:flying', 'Talonflame (Ashen, Flying)', 'BM3D_2627'),
('2628', '663', 'BM3D_2628', 'pixelmon:base:ashen:always', 'Talonflame (Ashen, State 1)', 'BM3D_2628'),
('2629', '666', 'BM3D_2629', 'pixelmon:base:strike:always', 'Vivillon (Strike)', 'BM3D_2629'),
('2630', '679', 'BM3D_2630', 'pixelmon:base:alter:always', 'Honedge (Alter)', 'BM3D_2630'),
('2631', '680', 'BM3D_2631', 'pixelmon:base:alter:always', 'Doublade (Alter)', 'BM3D_2631'),
('2632', '681', 'BM3D_2632', 'pixelmon:blade:alter:always', 'Aegislash (Blade, Alter)', 'BM3D_2632'),
('2633', '681', 'BM3D_2633', 'pixelmon:shield:alter:always', 'Aegislash (Shield, Alter)', 'BM3D_2633'),
('2634', '700', 'BM3D_2634', 'pixelmon:base:spirit:always', 'Sylveon (Spirit)', 'BM3D_2634'),
('2635', '716', 'BM3D_2635', 'pixelmon:active:creator:always', 'Xerneas (Active, Creator)', 'BM3D_2635'),
('2636', '716', 'BM3D_2636', 'pixelmon:neutral:creator:always', 'Xerneas (Neutral, Creator)', 'BM3D_2636'),
('2637', '747', 'BM3D_2637', 'pixelmon:base:spirit:always', 'Mareanie (Spirit)', 'BM3D_2637'),
('2638', '748', 'BM3D_2638', 'pixelmon:base:spirit:always', 'Toxapex (Spirit)', 'BM3D_2638'),
('2641', '771', 'BM3D_2641', 'pixelmon:base:alter:always', 'Pyukumuku (Alter)', 'BM3D_2641'),
('2642', '771', 'BM3D_2642', 'pixelmon:base:drowned:always', 'Pyukumuku (Drowned)', 'BM3D_2642'),
('2643', '778', 'BM3D_2643', 'pixelmon:busted:spirit:always', 'Mimikyu (Busted, Spirit)', 'BM3D_2643'),
('2644', '778', 'BM3D_2644', 'pixelmon:disguised:spirit:always', 'Mimikyu (Disguised, Spirit)', 'BM3D_2644'),
('2645', '780', 'BM3D_2645', 'pixelmon:base:christmas:always', 'Drampa (Christmas)', 'BM3D_2645'),
('2646', '791', 'BM3D_2646', 'pixelmon:base:real:always', 'Solgaleo (Real)', 'BM3D_2646'),
('2647', '793', 'BM3D_2647', 'pixelmon:base:none:always', 'Nihilego', 'BM3D_2647'),
('2649', '807', 'BM3D_2649', 'pixelmon:base:strike:always', 'Zeraora (Strike)', 'BM3D_2649'),
('2650', '809', 'BM3D_2650', 'pixelmon:gmax:none:always', 'Melmetal (Gmax)', 'BM3D_2650'),
('2652', '812', 'BM3D_2652', 'pixelmon:gmax:none:always', 'Rillaboom (Gmax)', 'BM3D_2652'),
('2654', '815', 'BM3D_2654', 'pixelmon:base:online:always', 'Cinderace (Online)', 'BM3D_2654'),
('2655', '815', 'BM3D_2655', 'pixelmon:gmax:none:always', 'Cinderace (Gmax)', 'BM3D_2655'),
('2656', '815', 'BM3D_2656', 'pixelmon:gmax:online:always', 'Cinderace (Gmax, Online)', 'BM3D_2656'),
('2658', '818', 'BM3D_2658', 'pixelmon:gmax:none:always', 'Inteleon (Gmax)', 'BM3D_2658'),
('2660', '821', 'BM3D_2660', 'pixelmon:base:none:flying', 'Rookidee (Flying)', 'BM3D_2660'),
('2662', '822', 'BM3D_2662', 'pixelmon:base:none:flying', 'Corvisquire (Flying)', 'BM3D_2662'),
('2664', '823', 'BM3D_2664', 'pixelmon:base:none:flying', 'Corviknight (Flying)', 'BM3D_2664'),
('2666', '823', 'BM3D_2666', 'pixelmon:gmax:none:always', 'Corviknight (Gmax)', 'BM3D_2666'),
('2668', '826', 'BM3D_2668', 'pixelmon:gmax:none:always', 'Orbeetle (Gmax)', 'BM3D_2668'),
('2670', '831', 'BM3D_2670', 'pixelmon:base:black:always', 'Wooloo (Black)', 'BM3D_2670'),
('2671', '831', 'BM3D_2671', 'pixelmon:base:blue:always', 'Wooloo (Blue)', 'BM3D_2671'),
('2672', '831', 'BM3D_2672', 'pixelmon:base:brown:always', 'Wooloo (Brown)', 'BM3D_2672'),
('2673', '831', 'BM3D_2673', 'pixelmon:base:cyan:always', 'Wooloo (Cyan)', 'BM3D_2673'),
('2674', '831', 'BM3D_2674', 'pixelmon:base:gray:always', 'Wooloo (Gray)', 'BM3D_2674'),
('2675', '831', 'BM3D_2675', 'pixelmon:base:green:always', 'Wooloo (Green)', 'BM3D_2675'),
('2676', '831', 'BM3D_2676', 'pixelmon:base:lightblue:always', 'Wooloo (Lightblue)', 'BM3D_2676'),
('2677', '831', 'BM3D_2677', 'pixelmon:base:lightgray:always', 'Wooloo (Lightgray)', 'BM3D_2677'),
('2678', '831', 'BM3D_2678', 'pixelmon:base:lime:always', 'Wooloo (Lime)', 'BM3D_2678'),
('2679', '831', 'BM3D_2679', 'pixelmon:base:magenta:always', 'Wooloo (Magenta)', 'BM3D_2679'),
('2680', '831', 'BM3D_2680', 'pixelmon:base:orange:always', 'Wooloo (Orange)', 'BM3D_2680'),
('2681', '831', 'BM3D_2681', 'pixelmon:base:pink:always', 'Wooloo (Pink)', 'BM3D_2681'),
('2682', '831', 'BM3D_2682', 'pixelmon:base:purple:always', 'Wooloo (Purple)', 'BM3D_2682'),
('2683', '831', 'BM3D_2683', 'pixelmon:base:red:always', 'Wooloo (Red)', 'BM3D_2683'),
('2684', '831', 'BM3D_2684', 'pixelmon:base:yellow:always', 'Wooloo (Yellow)', 'BM3D_2684'),
('2685', '831', 'BM3D_2685', 'pixelmon:shorn:black:always', 'Wooloo (Shorn, Black)', 'BM3D_2685'),
('2686', '831', 'BM3D_2686', 'pixelmon:shorn:blue:always', 'Wooloo (Shorn, Blue)', 'BM3D_2686'),
('2687', '831', 'BM3D_2687', 'pixelmon:shorn:brown:always', 'Wooloo (Shorn, Brown)', 'BM3D_2687'),
('2688', '831', 'BM3D_2688', 'pixelmon:shorn:cyan:always', 'Wooloo (Shorn, Cyan)', 'BM3D_2688'),
('2689', '831', 'BM3D_2689', 'pixelmon:shorn:gray:always', 'Wooloo (Shorn, Gray)', 'BM3D_2689'),
('2690', '831', 'BM3D_2690', 'pixelmon:shorn:green:always', 'Wooloo (Shorn, Green)', 'BM3D_2690'),
('2691', '831', 'BM3D_2691', 'pixelmon:shorn:lightblue:always', 'Wooloo (Shorn, Lightblue)', 'BM3D_2691'),
('2692', '831', 'BM3D_2692', 'pixelmon:shorn:lightgray:always', 'Wooloo (Shorn, Lightgray)', 'BM3D_2692'),
('2693', '831', 'BM3D_2693', 'pixelmon:shorn:lime:always', 'Wooloo (Shorn, Lime)', 'BM3D_2693'),
('2694', '831', 'BM3D_2694', 'pixelmon:shorn:magenta:always', 'Wooloo (Shorn, Magenta)', 'BM3D_2694'),
('2695', '831', 'BM3D_2695', 'pixelmon:shorn:none:always', 'Wooloo (Shorn)', 'BM3D_2695'),
('2696', '831', 'BM3D_2696', 'pixelmon:shorn:orange:always', 'Wooloo (Shorn, Orange)', 'BM3D_2696'),
('2697', '831', 'BM3D_2697', 'pixelmon:shorn:pink:always', 'Wooloo (Shorn, Pink)', 'BM3D_2697'),
('2698', '831', 'BM3D_2698', 'pixelmon:shorn:purple:always', 'Wooloo (Shorn, Purple)', 'BM3D_2698'),
('2699', '831', 'BM3D_2699', 'pixelmon:shorn:red:always', 'Wooloo (Shorn, Red)', 'BM3D_2699'),
('2701', '831', 'BM3D_2701', 'pixelmon:shorn:yellow:always', 'Wooloo (Shorn, Yellow)', 'BM3D_2701'),
('2702', '832', 'BM3D_2702', 'pixelmon:base:black:always', 'Dubwool (Black)', 'BM3D_2702'),
('2703', '832', 'BM3D_2703', 'pixelmon:base:blue:always', 'Dubwool (Blue)', 'BM3D_2703'),
('2704', '832', 'BM3D_2704', 'pixelmon:base:brown:always', 'Dubwool (Brown)', 'BM3D_2704'),
('2705', '832', 'BM3D_2705', 'pixelmon:base:cyan:always', 'Dubwool (Cyan)', 'BM3D_2705'),
('2706', '832', 'BM3D_2706', 'pixelmon:base:gray:always', 'Dubwool (Gray)', 'BM3D_2706'),
('2707', '832', 'BM3D_2707', 'pixelmon:base:green:always', 'Dubwool (Green)', 'BM3D_2707'),
('2708', '832', 'BM3D_2708', 'pixelmon:base:lightblue:always', 'Dubwool (Lightblue)', 'BM3D_2708'),
('2709', '832', 'BM3D_2709', 'pixelmon:base:lightgray:always', 'Dubwool (Lightgray)', 'BM3D_2709'),
('2710', '832', 'BM3D_2710', 'pixelmon:base:lime:always', 'Dubwool (Lime)', 'BM3D_2710'),
('2711', '832', 'BM3D_2711', 'pixelmon:base:magenta:always', 'Dubwool (Magenta)', 'BM3D_2711'),
('2712', '832', 'BM3D_2712', 'pixelmon:base:orange:always', 'Dubwool (Orange)', 'BM3D_2712'),
('2713', '832', 'BM3D_2713', 'pixelmon:base:pink:always', 'Dubwool (Pink)', 'BM3D_2713'),
('2714', '832', 'BM3D_2714', 'pixelmon:base:purple:always', 'Dubwool (Purple)', 'BM3D_2714'),
('2715', '832', 'BM3D_2715', 'pixelmon:base:red:always', 'Dubwool (Red)', 'BM3D_2715'),
('2716', '832', 'BM3D_2716', 'pixelmon:base:yellow:always', 'Dubwool (Yellow)', 'BM3D_2716'),
('2717', '832', 'BM3D_2717', 'pixelmon:shorn:black:always', 'Dubwool (Shorn, Black)', 'BM3D_2717'),
('2718', '832', 'BM3D_2718', 'pixelmon:shorn:blue:always', 'Dubwool (Shorn, Blue)', 'BM3D_2718'),
('2719', '832', 'BM3D_2719', 'pixelmon:shorn:brown:always', 'Dubwool (Shorn, Brown)', 'BM3D_2719'),
('2720', '832', 'BM3D_2720', 'pixelmon:shorn:cyan:always', 'Dubwool (Shorn, Cyan)', 'BM3D_2720'),
('2721', '832', 'BM3D_2721', 'pixelmon:shorn:gray:always', 'Dubwool (Shorn, Gray)', 'BM3D_2721'),
('2722', '832', 'BM3D_2722', 'pixelmon:shorn:green:always', 'Dubwool (Shorn, Green)', 'BM3D_2722'),
('2723', '832', 'BM3D_2723', 'pixelmon:shorn:lightblue:always', 'Dubwool (Shorn, Lightblue)', 'BM3D_2723'),
('2724', '832', 'BM3D_2724', 'pixelmon:shorn:lightgray:always', 'Dubwool (Shorn, Lightgray)', 'BM3D_2724'),
('2725', '832', 'BM3D_2725', 'pixelmon:shorn:lime:always', 'Dubwool (Shorn, Lime)', 'BM3D_2725'),
('2726', '832', 'BM3D_2726', 'pixelmon:shorn:magenta:always', 'Dubwool (Shorn, Magenta)', 'BM3D_2726'),
('2727', '832', 'BM3D_2727', 'pixelmon:shorn:none:always', 'Dubwool (Shorn)', 'BM3D_2727'),
('2728', '832', 'BM3D_2728', 'pixelmon:shorn:orange:always', 'Dubwool (Shorn, Orange)', 'BM3D_2728'),
('2729', '832', 'BM3D_2729', 'pixelmon:shorn:pink:always', 'Dubwool (Shorn, Pink)', 'BM3D_2729'),
('2730', '832', 'BM3D_2730', 'pixelmon:shorn:purple:always', 'Dubwool (Shorn, Purple)', 'BM3D_2730'),
('2731', '832', 'BM3D_2731', 'pixelmon:shorn:red:always', 'Dubwool (Shorn, Red)', 'BM3D_2731'),
('2733', '832', 'BM3D_2733', 'pixelmon:shorn:yellow:always', 'Dubwool (Shorn, Yellow)', 'BM3D_2733'),
('2734', '834', 'BM3D_2734', 'pixelmon:gmax:none:always', 'Drednaw (Gmax)', 'BM3D_2734'),
('2736', '835', 'BM3D_2736', 'pixelmon:base:strike:always', 'Yamper (Strike)', 'BM3D_2736'),
('2737', '836', 'BM3D_2737', 'pixelmon:base:strike:always', 'Boltund (Strike)', 'BM3D_2737'),
('2738', '839', 'BM3D_2738', 'pixelmon:base:none:always', 'Coalossal', 'BM3D_2738'),
('2740', '839', 'BM3D_2740', 'pixelmon:gmax:none:always', 'Coalossal (Gmax)', 'BM3D_2740'),
('2742', '841', 'BM3D_2742', 'pixelmon:gmax:none:always', 'Flapple (Gmax)', 'BM3D_2742'),
('2744', '842', 'BM3D_2744', 'pixelmon:gmax:none:always', 'Appletun (Gmax)', 'BM3D_2744'),
('2746', '844', 'BM3D_2746', 'pixelmon:gmax:none:always', 'Sandaconda (Gmax)', 'BM3D_2746'),
('2748', '849', 'BM3D_2748', 'pixelmon:gmax:none:always', 'Toxtricity (Gmax)', 'BM3D_2748'),
('2750', '851', 'BM3D_2750', 'pixelmon:base:ashen:always', 'Centiskorch (Ashen)', 'BM3D_2750'),
('2751', '851', 'BM3D_2751', 'pixelmon:gmax:ashen:always', 'Centiskorch (Gmax, Ashen)', 'BM3D_2751'),
('2752', '851', 'BM3D_2752', 'pixelmon:gmax:none:always', 'Centiskorch (Gmax)', 'BM3D_2752'),
('2754', '852', 'BM3D_2754', 'pixelmon:base:alien:always', 'Clobbopus (Alien)', 'BM3D_2754'),
('2755', '852', 'BM3D_2755', 'pixelmon:base:clubs:always', 'Clobbopus (Clubs)', 'BM3D_2755'),
('2756', '852', 'BM3D_2756', 'pixelmon:base:diamonds:always', 'Clobbopus (Diamonds)', 'BM3D_2756'),
('2757', '852', 'BM3D_2757', 'pixelmon:base:irish:always', 'Clobbopus (Irish)', 'BM3D_2757'),
('2758', '852', 'BM3D_2758', 'pixelmon:base:martian:always', 'Clobbopus (Martian)', 'BM3D_2758'),
('2759', '852', 'BM3D_2759', 'pixelmon:base:red_ringed:always', 'Clobbopus (Red Ringed)', 'BM3D_2759'),
('2760', '852', 'BM3D_2760', 'pixelmon:base:starry:always', 'Clobbopus (Starry)', 'BM3D_2760'),
('2761', '852', 'BM3D_2761', 'pixelmon:base:yellow_ringed:always', 'Clobbopus (Yellow Ringed)', 'BM3D_2761'),
('2762', '853', 'BM3D_2762', 'pixelmon:base:alien:always', 'Grapploct (Alien)', 'BM3D_2762'),
('2763', '853', 'BM3D_2763', 'pixelmon:base:clubs:always', 'Grapploct (Clubs)', 'BM3D_2763'),
('2764', '853', 'BM3D_2764', 'pixelmon:base:diamonds:always', 'Grapploct (Diamonds)', 'BM3D_2764'),
('2765', '853', 'BM3D_2765', 'pixelmon:base:irish:always', 'Grapploct (Irish)', 'BM3D_2765'),
('2766', '853', 'BM3D_2766', 'pixelmon:base:martian:always', 'Grapploct (Martian)', 'BM3D_2766'),
('2767', '853', 'BM3D_2767', 'pixelmon:base:red_ringed:always', 'Grapploct (Red Ringed)', 'BM3D_2767'),
('2768', '853', 'BM3D_2768', 'pixelmon:base:starry:always', 'Grapploct (Starry)', 'BM3D_2768'),
('2769', '853', 'BM3D_2769', 'pixelmon:base:yellow_ringed:always', 'Grapploct (Yellow Ringed)', 'BM3D_2769'),
('2770', '854', 'BM3D_2770', 'pixelmon:antique:christmas:always', 'Sinistea (Antique, Christmas)', 'BM3D_2770'),
('2771', '854', 'BM3D_2771', 'pixelmon:antique:none:always', 'Sinistea (Antique)', 'BM3D_2771'),
('2773', '854', 'BM3D_2773', 'pixelmon:phony:christmas:always', 'Sinistea (Phony, Christmas)', 'BM3D_2773'),
('2774', '855', 'BM3D_2774', 'pixelmon:antique:none:always', 'Polteageist (Antique)', 'BM3D_2774'),
('2776', '858', 'BM3D_2776', 'pixelmon:gmax:none:always', 'Hatterene (Gmax)', 'BM3D_2776'),
('2778', '861', 'BM3D_2778', 'pixelmon:gmax:none:always', 'Grimmsnarl (Gmax)', 'BM3D_2778'),
('2780', '869', 'BM3D_2780', 'pixelmon:base:pumpkin:always', 'Alcremie (Pumpkin)', 'BM3D_2780'),
('2781', '869', 'BM3D_2781', 'pixelmon:base:pumpkin_shiny:always', 'Alcremie (Pumpkin Shiny)', 'BM3D_2781'),
('2782', '869', 'BM3D_2782', 'pixelmon:gmax:berry_caramel_swirl:always', 'Alcremie (Gmax, Berry Caramel Swirl)', 'BM3D_2782'),
('2783', '869', 'BM3D_2783', 'pixelmon:gmax:berry_lemon_cream:always', 'Alcremie (Gmax, Berry Lemon Cream)', 'BM3D_2783'),
('2784', '869', 'BM3D_2784', 'pixelmon:gmax:berry_matcha_cream:always', 'Alcremie (Gmax, Berry Matcha Cream)', 'BM3D_2784'),
('2785', '869', 'BM3D_2785', 'pixelmon:gmax:berry_mint_cream:always', 'Alcremie (Gmax, Berry Mint Cream)', 'BM3D_2785'),
('2786', '869', 'BM3D_2786', 'pixelmon:gmax:berry_rainbow_swirl:always', 'Alcremie (Gmax, Berry Rainbow Swirl)', 'BM3D_2786'),
('2787', '869', 'BM3D_2787', 'pixelmon:gmax:berry_ruby_cream:always', 'Alcremie (Gmax, Berry Ruby Cream)', 'BM3D_2787'),
('2788', '869', 'BM3D_2788', 'pixelmon:gmax:berry_ruby_swirl:always', 'Alcremie (Gmax, Berry Ruby Swirl)', 'BM3D_2788'),
('2789', '869', 'BM3D_2789', 'pixelmon:gmax:berry_salted_cream:always', 'Alcremie (Gmax, Berry Salted Cream)', 'BM3D_2789'),
('2790', '869', 'BM3D_2790', 'pixelmon:gmax:berry_shiny:always', 'Alcremie (Gmax, Berry Shiny)', 'BM3D_2790'),
('2791', '869', 'BM3D_2791', 'pixelmon:gmax:berry_vanilla_cream:always', 'Alcremie (Gmax, Berry Vanilla Cream)', 'BM3D_2791'),
('2792', '869', 'BM3D_2792', 'pixelmon:gmax:clover_caramel_swirl:always', 'Alcremie (Gmax, Clover Caramel Swirl)', 'BM3D_2792'),
('2793', '869', 'BM3D_2793', 'pixelmon:gmax:clover_lemon_cream:always', 'Alcremie (Gmax, Clover Lemon Cream)', 'BM3D_2793'),
('2794', '869', 'BM3D_2794', 'pixelmon:gmax:clover_matcha_cream:always', 'Alcremie (Gmax, Clover Matcha Cream)', 'BM3D_2794'),
('2795', '869', 'BM3D_2795', 'pixelmon:gmax:clover_mint_cream:always', 'Alcremie (Gmax, Clover Mint Cream)', 'BM3D_2795'),
('2796', '869', 'BM3D_2796', 'pixelmon:gmax:clover_rainbow_swirl:always', 'Alcremie (Gmax, Clover Rainbow Swirl)', 'BM3D_2796'),
('2797', '869', 'BM3D_2797', 'pixelmon:gmax:clover_ruby_cream:always', 'Alcremie (Gmax, Clover Ruby Cream)', 'BM3D_2797'),
('2798', '869', 'BM3D_2798', 'pixelmon:gmax:clover_ruby_swirl:always', 'Alcremie (Gmax, Clover Ruby Swirl)', 'BM3D_2798'),
('2799', '869', 'BM3D_2799', 'pixelmon:gmax:clover_salted_cream:always', 'Alcremie (Gmax, Clover Salted Cream)', 'BM3D_2799'),
('2800', '869', 'BM3D_2800', 'pixelmon:gmax:clover_shiny:always', 'Alcremie (Gmax, Clover Shiny)', 'BM3D_2800'),
('2801', '869', 'BM3D_2801', 'pixelmon:gmax:clover_vanilla_cream:always', 'Alcremie (Gmax, Clover Vanilla Cream)', 'BM3D_2801'),
('2802', '869', 'BM3D_2802', 'pixelmon:gmax:flower_caramel_swirl:always', 'Alcremie (Gmax, Flower Caramel Swirl)', 'BM3D_2802'),
('2803', '869', 'BM3D_2803', 'pixelmon:gmax:flower_lemon_cream:always', 'Alcremie (Gmax, Flower Lemon Cream)', 'BM3D_2803'),
('2804', '869', 'BM3D_2804', 'pixelmon:gmax:flower_matcha_cream:always', 'Alcremie (Gmax, Flower Matcha Cream)', 'BM3D_2804'),
('2805', '869', 'BM3D_2805', 'pixelmon:gmax:flower_mint_cream:always', 'Alcremie (Gmax, Flower Mint Cream)', 'BM3D_2805'),
('2806', '869', 'BM3D_2806', 'pixelmon:gmax:flower_rainbow_swirl:always', 'Alcremie (Gmax, Flower Rainbow Swirl)', 'BM3D_2806'),
('2807', '869', 'BM3D_2807', 'pixelmon:gmax:flower_ruby_cream:always', 'Alcremie (Gmax, Flower Ruby Cream)', 'BM3D_2807'),
('2808', '869', 'BM3D_2808', 'pixelmon:gmax:flower_ruby_swirl:always', 'Alcremie (Gmax, Flower Ruby Swirl)', 'BM3D_2808'),
('2809', '869', 'BM3D_2809', 'pixelmon:gmax:flower_salted_cream:always', 'Alcremie (Gmax, Flower Salted Cream)', 'BM3D_2809'),
('2810', '869', 'BM3D_2810', 'pixelmon:gmax:flower_shiny:always', 'Alcremie (Gmax, Flower Shiny)', 'BM3D_2810'),
('2811', '869', 'BM3D_2811', 'pixelmon:gmax:flower_vanilla_cream:always', 'Alcremie (Gmax, Flower Vanilla Cream)', 'BM3D_2811'),
('2812', '869', 'BM3D_2812', 'pixelmon:gmax:love_caramel_swirl:always', 'Alcremie (Gmax, Love Caramel Swirl)', 'BM3D_2812'),
('2813', '869', 'BM3D_2813', 'pixelmon:gmax:love_lemon_cream:always', 'Alcremie (Gmax, Love Lemon Cream)', 'BM3D_2813'),
('2814', '869', 'BM3D_2814', 'pixelmon:gmax:love_matcha_cream:always', 'Alcremie (Gmax, Love Matcha Cream)', 'BM3D_2814'),
('2815', '869', 'BM3D_2815', 'pixelmon:gmax:love_mint_cream:always', 'Alcremie (Gmax, Love Mint Cream)', 'BM3D_2815'),
('2816', '869', 'BM3D_2816', 'pixelmon:gmax:love_rainbow_swirl:always', 'Alcremie (Gmax, Love Rainbow Swirl)', 'BM3D_2816'),
('2817', '869', 'BM3D_2817', 'pixelmon:gmax:love_ruby_cream:always', 'Alcremie (Gmax, Love Ruby Cream)', 'BM3D_2817'),
('2818', '869', 'BM3D_2818', 'pixelmon:gmax:love_ruby_swirl:always', 'Alcremie (Gmax, Love Ruby Swirl)', 'BM3D_2818'),
('2819', '869', 'BM3D_2819', 'pixelmon:gmax:love_salted_cream:always', 'Alcremie (Gmax, Love Salted Cream)', 'BM3D_2819'),
('2820', '869', 'BM3D_2820', 'pixelmon:gmax:love_shiny:always', 'Alcremie (Gmax, Love Shiny)', 'BM3D_2820'),
('2821', '869', 'BM3D_2821', 'pixelmon:gmax:love_vanilla_cream:always', 'Alcremie (Gmax, Love Vanilla Cream)', 'BM3D_2821'),
('2822', '869', 'BM3D_2822', 'pixelmon:gmax:none:always', 'Alcremie (Gmax)', 'BM3D_2822'),
('2823', '869', 'BM3D_2823', 'pixelmon:gmax:pumpkin:always', 'Alcremie (Gmax, Pumpkin)', 'BM3D_2823'),
('2824', '869', 'BM3D_2824', 'pixelmon:gmax:pumpkin_shiny:always', 'Alcremie (Gmax, Pumpkin Shiny)', 'BM3D_2824'),
('2825', '869', 'BM3D_2825', 'pixelmon:gmax:ribbon_caramel_swirl:always', 'Alcremie (Gmax, Ribbon Caramel Swirl)', 'BM3D_2825'),
('2826', '869', 'BM3D_2826', 'pixelmon:gmax:ribbon_lemon_cream:always', 'Alcremie (Gmax, Ribbon Lemon Cream)', 'BM3D_2826'),
('2827', '869', 'BM3D_2827', 'pixelmon:gmax:ribbon_matcha_cream:always', 'Alcremie (Gmax, Ribbon Matcha Cream)', 'BM3D_2827'),
('2828', '869', 'BM3D_2828', 'pixelmon:gmax:ribbon_mint_cream:always', 'Alcremie (Gmax, Ribbon Mint Cream)', 'BM3D_2828'),
('2829', '869', 'BM3D_2829', 'pixelmon:gmax:ribbon_rainbow_swirl:always', 'Alcremie (Gmax, Ribbon Rainbow Swirl)', 'BM3D_2829'),
('2830', '869', 'BM3D_2830', 'pixelmon:gmax:ribbon_ruby_cream:always', 'Alcremie (Gmax, Ribbon Ruby Cream)', 'BM3D_2830'),
('2831', '869', 'BM3D_2831', 'pixelmon:gmax:ribbon_ruby_swirl:always', 'Alcremie (Gmax, Ribbon Ruby Swirl)', 'BM3D_2831'),
('2832', '869', 'BM3D_2832', 'pixelmon:gmax:ribbon_salted_cream:always', 'Alcremie (Gmax, Ribbon Salted Cream)', 'BM3D_2832'),
('2833', '869', 'BM3D_2833', 'pixelmon:gmax:ribbon_shiny:always', 'Alcremie (Gmax, Ribbon Shiny)', 'BM3D_2833'),
('2834', '869', 'BM3D_2834', 'pixelmon:gmax:ribbon_vanilla_cream:always', 'Alcremie (Gmax, Ribbon Vanilla Cream)', 'BM3D_2834'),
('2836', '869', 'BM3D_2836', 'pixelmon:gmax:star_caramel_swirl:always', 'Alcremie (Gmax, Star Caramel Swirl)', 'BM3D_2836'),
('2837', '869', 'BM3D_2837', 'pixelmon:gmax:star_lemon_cream:always', 'Alcremie (Gmax, Star Lemon Cream)', 'BM3D_2837'),
('2838', '869', 'BM3D_2838', 'pixelmon:gmax:star_matcha_cream:always', 'Alcremie (Gmax, Star Matcha Cream)', 'BM3D_2838'),
('2839', '869', 'BM3D_2839', 'pixelmon:gmax:star_mint_cream:always', 'Alcremie (Gmax, Star Mint Cream)', 'BM3D_2839'),
('2840', '869', 'BM3D_2840', 'pixelmon:gmax:star_rainbow_swirl:always', 'Alcremie (Gmax, Star Rainbow Swirl)', 'BM3D_2840'),
('2841', '869', 'BM3D_2841', 'pixelmon:gmax:star_ruby_cream:always', 'Alcremie (Gmax, Star Ruby Cream)', 'BM3D_2841'),
('2842', '869', 'BM3D_2842', 'pixelmon:gmax:star_ruby_swirl:always', 'Alcremie (Gmax, Star Ruby Swirl)', 'BM3D_2842'),
('2843', '869', 'BM3D_2843', 'pixelmon:gmax:star_salted_cream:always', 'Alcremie (Gmax, Star Salted Cream)', 'BM3D_2843'),
('2844', '869', 'BM3D_2844', 'pixelmon:gmax:star_shiny:always', 'Alcremie (Gmax, Star Shiny)', 'BM3D_2844'),
('2845', '869', 'BM3D_2845', 'pixelmon:gmax:star_vanilla_cream:always', 'Alcremie (Gmax, Star Vanilla Cream)', 'BM3D_2845'),
('2846', '869', 'BM3D_2846', 'pixelmon:gmax:strawberry_caramel_swirl:always', 'Alcremie (Gmax, Strawberry Caramel Swirl)', 'BM3D_2846'),
('2847', '869', 'BM3D_2847', 'pixelmon:gmax:strawberry_lemon_cream:always', 'Alcremie (Gmax, Strawberry Lemon Cream)', 'BM3D_2847'),
('2848', '869', 'BM3D_2848', 'pixelmon:gmax:strawberry_matcha_cream:always', 'Alcremie (Gmax, Strawberry Matcha Cream)', 'BM3D_2848'),
('2849', '869', 'BM3D_2849', 'pixelmon:gmax:strawberry_mint_cream:always', 'Alcremie (Gmax, Strawberry Mint Cream)', 'BM3D_2849'),
('2850', '869', 'BM3D_2850', 'pixelmon:gmax:strawberry_rainbow_swirl:always', 'Alcremie (Gmax, Strawberry Rainbow Swirl)', 'BM3D_2850'),
('2851', '869', 'BM3D_2851', 'pixelmon:gmax:strawberry_ruby_cream:always', 'Alcremie (Gmax, Strawberry Ruby Cream)', 'BM3D_2851'),
('2852', '869', 'BM3D_2852', 'pixelmon:gmax:strawberry_ruby_swirl:always', 'Alcremie (Gmax, Strawberry Ruby Swirl)', 'BM3D_2852'),
('2853', '869', 'BM3D_2853', 'pixelmon:gmax:strawberry_salted_cream:always', 'Alcremie (Gmax, Strawberry Salted Cream)', 'BM3D_2853'),
('2854', '869', 'BM3D_2854', 'pixelmon:gmax:strawberry_shiny:always', 'Alcremie (Gmax, Strawberry Shiny)', 'BM3D_2854'),
('2855', '869', 'BM3D_2855', 'pixelmon:gmax:strawberry_vanilla_cream:always', 'Alcremie (Gmax, Strawberry Vanilla Cream)', 'BM3D_2855'),
('2856', '879', 'BM3D_2856', 'pixelmon:gmax:none:always', 'Copperajah (Gmax)', 'BM3D_2856'),
('2858', '884', 'BM3D_2858', 'pixelmon:gmax:none:always', 'Duraludon (Gmax)', 'BM3D_2858'),
('2860', '885', 'BM3D_2860', 'pixelmon:base:spirit:always', 'Dreepy (Spirit)', 'BM3D_2860'),
('2861', '886', 'BM3D_2861', 'pixelmon:base:spirit:always', 'Drakloak (Spirit)', 'BM3D_2861'),
('2862', '887', 'BM3D_2862', 'pixelmon:base:spirit:always', 'Dragapult (Spirit)', 'BM3D_2862'),
('2863', '890', 'BM3D_2863', 'pixelmon:eternamax:none:always', 'Eternatus (Eternamax)', 'BM3D_2863'),
('2865', '890', 'BM3D_2865', 'pixelmon:ordinary:cosmetic:always', 'Eternatus (Ordinary, Cosmetic)', 'BM3D_2865'),
('2866', '890', 'BM3D_2866', 'pixelmon:ordinary:shiny_cosmetic:always', 'Eternatus (Ordinary, Shiny Cosmetic)', 'BM3D_2866'),
('2867', '892', 'BM3D_2867', 'pixelmon:gmaxrs:none:always', 'Urshifu (Gmaxrs)', 'BM3D_2867'),
('2869', '892', 'BM3D_2869', 'pixelmon:gmaxss:none:always', 'Urshifu (Gmaxss)', 'BM3D_2869'),
('2871', '894', 'BM3D_2871', 'pixelmon:base:spirit:always', 'Regieleki (Spirit)', 'BM3D_2871'),
('2872', '897', 'BM3D_2872', 'pixelmon:base:none:always', 'Spectrier', 'BM3D_2872'),
('2874', '901', 'BM3D_2874', 'pixelmon:bloodmoon:none:always', 'Ursaluna (Bloodmoon)', 'BM3D_2874'),
('2876', '906', 'BM3D_2876', 'pixelmon:base:autumn:always', 'Sprigatito (Autumn)', 'BM3D_2876'),
('2877', '906', 'BM3D_2877', 'pixelmon:base:spring:always', 'Sprigatito (Spring)', 'BM3D_2877'),
('2878', '906', 'BM3D_2878', 'pixelmon:base:summer:always', 'Sprigatito (Summer)', 'BM3D_2878'),
('2879', '906', 'BM3D_2879', 'pixelmon:base:winter:always', 'Sprigatito (Winter)', 'BM3D_2879'),
('2880', '907', 'BM3D_2880', 'pixelmon:base:autumn:always', 'Floragato (Autumn)', 'BM3D_2880'),
('2881', '907', 'BM3D_2881', 'pixelmon:base:spring:always', 'Floragato (Spring)', 'BM3D_2881'),
('2882', '907', 'BM3D_2882', 'pixelmon:base:summer:always', 'Floragato (Summer)', 'BM3D_2882'),
('2883', '907', 'BM3D_2883', 'pixelmon:base:winter:always', 'Floragato (Winter)', 'BM3D_2883'),
('2884', '908', 'BM3D_2884', 'pixelmon:base:autumn:always', 'Meowscarada (Autumn)', 'BM3D_2884'),
('2885', '908', 'BM3D_2885', 'pixelmon:base:spring:always', 'Meowscarada (Spring)', 'BM3D_2885'),
('2886', '908', 'BM3D_2886', 'pixelmon:base:summer:always', 'Meowscarada (Summer)', 'BM3D_2886'),
('2887', '908', 'BM3D_2887', 'pixelmon:base:winter:always', 'Meowscarada (Winter)', 'BM3D_2887'),
('2888', '921', 'BM3D_2888', 'pixelmon:base:christmas:always', 'Pawmi (Christmas)', 'BM3D_2888'),
('2889', '921', 'BM3D_2889', 'pixelmon:base:elf:always', 'Pawmi (Elf)', 'BM3D_2889'),
('2890', '922', 'BM3D_2890', 'pixelmon:base:christmas:always', 'Pawmo (Christmas)', 'BM3D_2890'),
('2891', '922', 'BM3D_2891', 'pixelmon:base:elf:always', 'Pawmo (Elf)', 'BM3D_2891'),
('2892', '923', 'BM3D_2892', 'pixelmon:base:christmas:always', 'Pawmot (Christmas)', 'BM3D_2892'),
('2893', '923', 'BM3D_2893', 'pixelmon:base:elf:always', 'Pawmot (Elf)', 'BM3D_2893'),
('2894', '934', 'BM3D_2894', 'pixelmon:base:none:always', 'Garganacl', 'BM3D_2894'),
('2896', '935', 'BM3D_2896', 'pixelmon:base:none:always', 'Charcadet', 'BM3D_2896'),
('2898', '936', 'BM3D_2898', 'pixelmon:base:none:always', 'Armarouge', 'BM3D_2898'),
('2900', '937', 'BM3D_2900', 'pixelmon:base:none:always', 'Ceruledge', 'BM3D_2900'),
('2902', '939', 'BM3D_2902', 'pixelmon:base:none:always', 'Bellibolt', 'BM3D_2902'),
('2904', '946', 'BM3D_2904', 'pixelmon:base:tangela:always', 'Bramblin (Tangela)', 'BM3D_2904'),
('2905', '947', 'BM3D_2905', 'pixelmon:base:tangela:always', 'Brambleghast (Tangela)', 'BM3D_2905'),
('2906', '957', 'BM3D_2906', 'pixelmon:base:witch:always', 'Tinkatink (Witch)', 'BM3D_2906'),
('2907', '958', 'BM3D_2907', 'pixelmon:base:witch:always', 'Tinkatuff (Witch)', 'BM3D_2907'),
('2908', '959', 'BM3D_2908', 'pixelmon:base:witch:always', 'Tinkaton (Witch)', 'BM3D_2908'),
('2909', '962', 'BM3D_2909', 'pixelmon:base:none:flying', 'Bombirdier (Flying)', 'BM3D_2909'),
('2911', '967', 'BM3D_2911', 'pixelmon:base:none:walk', 'Cyclizar (Walk)', 'BM3D_2911'),
('2913', '971', 'BM3D_2913', 'pixelmon:base:none:always', 'Greavard', 'BM3D_2913'),
('2915', '971', 'BM3D_2915', 'pixelmon:base:witch:always', 'Greavard (Witch)', 'BM3D_2915'),
('2916', '972', 'BM3D_2916', 'pixelmon:base:witch:always', 'Houndstone (Witch)', 'BM3D_2916'),
('2917', '973', 'BM3D_2917', 'pixelmon:base:none:flying', 'Flamigo (Flying)', 'BM3D_2917'),
('2918', '973', 'BM3D_2918', 'pixelmon:base:rainbow:flying', 'Flamigo (Rainbow, Flying)', 'BM3D_2918'),
('2919', '973', 'BM3D_2919', 'pixelmon:base:rainbow:always', 'Flamigo (Rainbow, State 1)', 'BM3D_2919'),
('2921', '988', 'BM3D_2921', 'pixelmon:base:christmas:always', 'SlitherWing (Christmas)', 'BM3D_2921'),
('2922', '988', 'BM3D_2922', 'pixelmon:base:elf:always', 'SlitherWing (Elf)', 'BM3D_2922'),
('2923', '990', 'BM3D_2923', 'pixelmon:base:none:always', 'IronTreads', 'BM3D_2923'),
('2925', '991', 'BM3D_2925', 'pixelmon:base:none:always', 'IronBundle', 'BM3D_2925'),
('2927', '992', 'BM3D_2927', 'pixelmon:base:none:always', 'IronHands', 'BM3D_2927'),
('2929', '993', 'BM3D_2929', 'pixelmon:base:none:always', 'IronJugulis', 'BM3D_2929'),
('2931', '999', 'BM3D_2931', 'pixelmon:chest:gingerbread:always', 'Gimmighoul (Chest, Gingerbread)', 'BM3D_2931'),
('2932', '999', 'BM3D_2932', 'pixelmon:roaming:gingerbread:always', 'Gimmighoul (Roaming, Gingerbread)', 'BM3D_2932'),
('2933', '1002', 'BM3D_2933', 'pixelmon:base:rainbow:always', 'Chien-Pao (Rainbow)', 'BM3D_2933'),
('2934', '1006', 'BM3D_2934', 'pixelmon:base:none:always', 'IronValiant', 'BM3D_2934'),
('2936', '1006', 'BM3D_2936', 'pixelmon:base:spirit:always', 'IronValiant (Spirit)', 'BM3D_2936'),
('2937', '1007', 'BM3D_2937', 'pixelmon:base:none:flying', 'Koraidon (Flying)', 'BM3D_2937'),
('2938', '1007', 'BM3D_2938', 'pixelmon:base:none:riding', 'Koraidon (Riding, State 1)', 'BM3D_2938'),
('2941', '1007', 'BM3D_2941', 'pixelmon:base:shiny:riding', 'Koraidon (Riding, State 2)', 'BM3D_2941'),
('2942', '1008', 'BM3D_2942', 'pixelmon:base:none:riding', 'Miraidon (Riding)', 'BM3D_2942'),
('2943', '1008', 'BM3D_2943', 'pixelmon:base:none:riding', 'Miraidon (Riding, State 1)', 'BM3D_2943'),
('2944', '1008', 'BM3D_2944', 'pixelmon:base:shiny:riding', 'Miraidon (Riding)', 'BM3D_2944'),
('2946', '1010', 'BM3D_2946', 'pixelmon:base:christmas:always', 'IronLeaves (Christmas)', 'BM3D_2946'),
('2947', '1010', 'BM3D_2947', 'pixelmon:base:elf:always', 'IronLeaves (Elf)', 'BM3D_2947'),
('2948', '1010', 'BM3D_2948', 'pixelmon:base:none:always', 'IronLeaves', 'BM3D_2948'),
('2950', '1012', 'BM3D_2950', 'pixelmon:artisan:none:always', 'Poltchageist (Artisan)', 'BM3D_2950'),
('2952', '1013', 'BM3D_2952', 'pixelmon:masterpiece:none:always', 'Sinistcha (Masterpiece)', 'BM3D_2952'),
('2954', '1014', 'BM3D_2954', 'pixelmon:base:none:always', 'Okidogi', 'BM3D_2954'),
('2956', '1015', 'BM3D_2956', 'pixelmon:base:none:always', 'Munkidori', 'BM3D_2956'),
('2958', '1016', 'BM3D_2958', 'pixelmon:base:none:flying', 'Fezandipiti (Flying, State 1)', 'BM3D_2958'),
('2960', '1022', 'BM3D_2960', 'pixelmon:base:neon:always', 'IronBoulder (Neon)', 'BM3D_2960'),
('2961', '1022', 'BM3D_2961', 'pixelmon:base:none:always', 'IronBoulder', 'BM3D_2961'),
('2963', '1023', 'BM3D_2963', 'pixelmon:base:neon:always', 'IronCrown (Neon)', 'BM3D_2963'),
('2964', '1023', 'BM3D_2964', 'pixelmon:base:none:always', 'IronCrown', 'BM3D_2964'),
('2966', '1024', 'BM3D_2966', 'pixelmon:normal:none:always', 'Terapagos', 'BM3D_2966'),
('2968', '1024', 'BM3D_2968', 'pixelmon:terastal:none:always', 'Terapagos (Terastal)', 'BM3D_2968'),
('2970', '1025', 'BM3D_2970', 'pixelmon:base:none:walk', 'Pecharunt (Walk)', 'BM3D_2970'),
('2971', '1025', 'BM3D_2971', 'pixelmon:base:none:always', 'Pecharunt (State 1)', 'BM3D_2971'),
('2974', '1026', 'BM3D_2974', 'pixelmon:base:none:always', 'Browt', 'BM3D_2974'),
('2976', '1029', 'BM3D_2976', 'pixelmon:base:none:always', 'Pombon', 'BM3D_2976'),
('2978', '1032', 'BM3D_2978', 'pixelmon:base:none:always', 'Gecqua', 'BM3D_2978');

CREATE TEMPORARY TABLE `bm3d_species` LIKE `battlemon_species`;
DELETE FROM `bm3d_species`;
INSERT INTO `bm3d_species` (`id`, `internal_name`, `name`, `type1`, `type2`, `hp`, `atk`, `def`, `spa`, `spd`, `spe`, `gender_ratio`, `growth_rate`, `base_exp`, `catch_rate`, `happiness`, `ability1`, `ability2`, `hidden_ability`, `egg_groups`, `hatch_steps`, `height`, `weight`, `color`, `shape`, `habitat`, `category`, `pokedex`, `generation`, `evolutions`, `sprite`) VALUES
('1033', 'MISSINGNO', 'MissingNo', 'FLYING', 'NORMAL', '33', '136', '0', '6', '6', '29', 'Genderless', 'Slow', '64', '1', '50', 'ERROR', '', '', 'UNDISCOVERED', '5376', '3.0', '1590.8', '', '', '', '', '', '0', '', 'BM3D_2000'),
('1026', 'BROWT', 'Browt', 'GRASS', '', '60', '45', '52', '50', '52', '51', 'FemaleOneEighth', 'Parabolic', '62', '45', '50', 'OVERGROW', '', '', 'GRASS,FLYING', '5376', '0.3', '3.5', '', '', '', '', '', '10', '', 'BM3D_2974'),
('1029', 'POMBON', 'Pombon', 'FIRE', '', '55', '50', '57', '49', '52', '47', 'FemaleOneEighth', 'Parabolic', '62', '45', '50', 'BLAZE', '', '', 'FIELD', '5376', '0.4', '6.7', '', '', '', '', '', '10', '', 'BM3D_2976'),
('1032', 'GECQUA', 'Gecqua', 'WATER', '', '50', '50', '48', '50', '52', '60', 'FemaleOneEighth', 'Parabolic', '62', '45', '50', 'TORRENT', '', '', 'MONSTER,WATER_ONE', '5376', '0.3', '4.3', '', '', '', '', '', '10', '', 'BM3D_2978');

DROP PROCEDURE IF EXISTS `bm3d_guard`;
DELIMITER //
CREATE PROCEDURE `bm3d_guard`()
BEGIN
    -- This core's runtime creature loader reads `id`; base dumps may have an older `id1` layout.
    IF NOT EXISTS (SELECT 1 FROM `information_schema`.`COLUMNS`
        WHERE `TABLE_SCHEMA`=DATABASE() AND `TABLE_NAME`='creature' AND `COLUMN_NAME`='id') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Battlemon migration requires runtime creature.id schema';
    END IF;
    IF EXISTS (SELECT 1 FROM `battlemon_forms` `f` JOIN `bm3d_forms` `n` ON `f`.`id`=`n`.`id`
        WHERE `f`.`sprite`<>`n`.`sprite` OR `f`.`species_id`<>`n`.`species_id`) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='3D form ID collision; no catalog changes applied';
    END IF;
    IF EXISTS (SELECT 1 FROM `battlemon_species` `s` JOIN `bm3d_species` `n` ON `s`.`id`=`n`.`id`
        WHERE `s`.`internal_name`<>`n`.`internal_name`) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='3D species ID collision';
    END IF;
    IF EXISTS (SELECT 1 FROM `creature_template` `c` JOIN `bm3d_forms` `f` ON `c`.`entry`=1000000+`f`.`id`
        WHERE `c`.`ScriptName`<>'npc_battlemon_overworld') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='3D creature entry collision';
    END IF;
    IF EXISTS (SELECT 1 FROM `battlemon_form_moves` `m` WHERE `m`.`id` BETWEEN 300000 AND 300643
        AND NOT EXISTS (SELECT 1 FROM `bm3d_forms` `f` WHERE `f`.`id`=`m`.`form_id`)) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='3D move row ID collision';
    END IF;
    IF EXISTS (SELECT 1 FROM `creature_template_model` `m` WHERE `m`.`CreatureDisplayID` BETWEEN 400000 AND 400979
        AND NOT EXISTS (SELECT 1 FROM `creature_template` `t` WHERE `t`.`entry`=`m`.`CreatureID` AND `t`.`ScriptName`='npc_battlemon_overworld')) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='3D display ID collision';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM `creature_template` WHERE `entry`=60000 AND `ScriptName`='npc_battlemon_overworld') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Install base Battlemon overworld SQL first';
    END IF;
END//
DELIMITER ;
CALL `bm3d_guard`();
DROP PROCEDURE `bm3d_guard`;
START TRANSACTION;
DELETE `s` FROM `battlemon_species` `s` JOIN `bm3d_species` `n` ON `s`.`id`=`n`.`id`;
INSERT INTO `battlemon_species` SELECT * FROM `bm3d_species`;
DELETE `f` FROM `battlemon_forms` `f` JOIN `bm3d_forms` `n` ON `f`.`id`=`n`.`id`;
INSERT INTO `battlemon_forms` SELECT * FROM `bm3d_forms`;
DELETE `m` FROM `battlemon_form_moves` `m` JOIN `bm3d_forms` `f` ON `m`.`form_id`=`f`.`id`;
INSERT INTO `battlemon_form_moves` (`id`, `form_id`, `method`, `level`, `move_internal_name`) VALUES
('300000', '2000', 'level', '1', 'WATERGUN'),
('300001', '2000', 'level', '1', 'SKYATTACK'),
('300002', '2000', 'level', '1', 'PAYDAY'),
('300003', '2000', 'level', '1', 'BIND'),
('300004', '2064', 'level', '0', 'PSYCHIC'),
('300005', '2064', 'level', '1', 'SPEEDSWAP'),
('300006', '2064', 'level', '1', 'THUNDERSHOCK'),
('300007', '2064', 'level', '1', 'TAILWHIP'),
('300008', '2064', 'level', '1', 'QUICKATTACK'),
('300009', '2064', 'level', '1', 'THUNDERBOLT'),
('300010', '2064', 'tutor', '0', 'AGILITY'),
('300011', '2064', 'tutor', '0', 'ALLYSWITCH'),
('300012', '2064', 'tutor', '0', 'ATTRACT'),
('300013', '2064', 'tutor', '0', 'BODYSLAM'),
('300014', '2064', 'tutor', '0', 'BRICKBREAK'),
('300015', '2064', 'tutor', '0', 'CALMMIND'),
('300016', '2064', 'tutor', '0', 'CAPTIVATE'),
('300017', '2064', 'tutor', '0', 'CHARM'),
('300018', '2064', 'tutor', '0', 'CHARGEBEAM'),
('300019', '2064', 'tutor', '0', 'CONFIDE'),
('300020', '2064', 'tutor', '0', 'COUNTER'),
('300021', '2064', 'tutor', '0', 'COVET'),
('300022', '2064', 'tutor', '0', 'DEFENSECURL'),
('300023', '2064', 'tutor', '0', 'DIG'),
('300024', '2064', 'tutor', '0', 'DOUBLEEDGE'),
('300025', '2064', 'tutor', '0', 'DOUBLETEAM'),
('300026', '2064', 'tutor', '0', 'DRAININGKISS'),
('300027', '2064', 'tutor', '0', 'DYNAMICPUNCH'),
('300028', '2064', 'tutor', '0', 'ECHOEDVOICE'),
('300029', '2064', 'tutor', '0', 'ELECTRICTERRAIN'),
('300030', '2064', 'tutor', '0', 'ELECTROBALL'),
('300031', '2064', 'tutor', '0', 'ELECTROWEB'),
('300032', '2064', 'tutor', '0', 'ENCORE'),
('300033', '2064', 'tutor', '0', 'ENDURE'),
('300034', '2064', 'tutor', '0', 'EXPANDINGFORCE'),
('300035', '2064', 'tutor', '0', 'FACADE'),
('300036', '2064', 'tutor', '0', 'FLASH'),
('300037', '2064', 'tutor', '0', 'FLING'),
('300038', '2064', 'tutor', '0', 'FOCUSBLAST'),
('300039', '2064', 'tutor', '0', 'FOCUSPUNCH'),
('300040', '2064', 'tutor', '0', 'FRUSTRATION'),
('300041', '2064', 'tutor', '0', 'FUTURESIGHT'),
('300042', '2064', 'tutor', '0', 'GIGAIMPACT'),
('300043', '2064', 'tutor', '0', 'GRASSKNOT'),
('300044', '2064', 'tutor', '0', 'HEADBUTT'),
('300045', '2064', 'tutor', '0', 'HELPINGHAND'),
('300046', '2064', 'tutor', '0', 'HIDDENPOWER'),
('300047', '2064', 'tutor', '0', 'HYPERBEAM'),
('300048', '2064', 'tutor', '0', 'IRONTAIL'),
('300049', '2064', 'tutor', '0', 'KNOCKOFF'),
('300050', '2064', 'tutor', '0', 'LASERFOCUS'),
('300051', '2064', 'tutor', '0', 'LIGHTSCREEN'),
('300052', '2064', 'tutor', '0', 'MAGICCOAT'),
('300053', '2064', 'tutor', '0', 'MAGICROOM'),
('300054', '2064', 'tutor', '0', 'MAGNETRISE'),
('300055', '2064', 'tutor', '0', 'MEGAKICK'),
('300056', '2064', 'tutor', '0', 'MEGAPUNCH'),
('300057', '2064', 'tutor', '0', 'MIMIC'),
('300058', '2064', 'tutor', '0', 'MUDSLAP'),
('300059', '2064', 'tutor', '0', 'NASTYPLOT'),
('300060', '2064', 'tutor', '0', 'NATURALGIFT'),
('300061', '2064', 'tutor', '0', 'PAYDAY'),
('300062', '2064', 'tutor', '0', 'PLAYROUGH'),
('300063', '2064', 'tutor', '0', 'PROTECT'),
('300064', '2064', 'tutor', '0', 'PSYCHIC'),
('300065', '2064', 'tutor', '0', 'PSYSHOCK'),
('300066', '2064', 'tutor', '0', 'RAINDANCE'),
('300067', '2064', 'tutor', '0', 'RECYCLE'),
('300068', '2064', 'tutor', '0', 'REFLECT'),
('300069', '2064', 'tutor', '0', 'REST'),
('300070', '2064', 'tutor', '0', 'RETURN'),
('300071', '2064', 'tutor', '0', 'REVERSAL'),
('300072', '2064', 'tutor', '0', 'RISINGVOLTAGE'),
('300073', '2064', 'tutor', '0', 'ROCKSMASH'),
('300074', '2064', 'tutor', '0', 'ROLLOUT'),
('300075', '2064', 'tutor', '0', 'ROUND'),
('300076', '2064', 'tutor', '0', 'SAFEGUARD'),
('300077', '2064', 'tutor', '0', 'SECRETPOWER'),
('300078', '2064', 'tutor', '0', 'SEISMICTOSS'),
('300079', '2064', 'tutor', '0', 'SHOCKWAVE'),
('300080', '2064', 'tutor', '0', 'SIGNALBEAM'),
('300081', '2064', 'tutor', '0', 'SLEEPTALK'),
('300082', '2064', 'tutor', '0', 'SNORE'),
('300083', '2064', 'tutor', '0', 'SPEEDSWAP'),
('300084', '2064', 'tutor', '0', 'STOREDPOWER'),
('300085', '2064', 'tutor', '0', 'STRENGTH'),
('300086', '2064', 'tutor', '0', 'SUBSTITUTE'),
('300087', '2064', 'tutor', '0', 'SURF'),
('300088', '2064', 'tutor', '0', 'SWAGGER'),
('300089', '2064', 'tutor', '0', 'SWIFT'),
('300090', '2064', 'tutor', '0', 'TELEKINESIS'),
('300091', '2064', 'tutor', '0', 'THIEF'),
('300092', '2064', 'tutor', '0', 'THUNDER'),
('300093', '2064', 'tutor', '0', 'THUNDERBOLT'),
('300094', '2064', 'tutor', '0', 'THUNDERPUNCH'),
('300095', '2064', 'tutor', '0', 'THUNDERWAVE'),
('300096', '2064', 'tutor', '0', 'UPROAR'),
('300097', '2064', 'tutor', '0', 'VOLTSWITCH'),
('300098', '2064', 'tutor', '0', 'WILDCHARGE'),
('300099', '2067', 'level', '1', 'SCRATCH'),
('300100', '2067', 'level', '1', 'DEFENSECURL'),
('300101', '2067', 'level', '3', 'BIDE'),
('300102', '2067', 'level', '5', 'POWDERSNOW'),
('300103', '2067', 'level', '7', 'ICEBALL'),
('300104', '2067', 'level', '9', 'RAPIDSPIN'),
('300105', '2067', 'level', '11', 'FURYCUTTER'),
('300106', '2067', 'level', '14', 'METALCLAW'),
('300107', '2067', 'level', '17', 'SWIFT'),
('300108', '2067', 'level', '20', 'FURYSWIPES'),
('300109', '2067', 'level', '23', 'IRONDEFENSE'),
('300110', '2067', 'level', '26', 'SLASH'),
('300111', '2067', 'level', '30', 'IRONHEAD'),
('300112', '2067', 'level', '34', 'GYROBALL'),
('300113', '2067', 'level', '38', 'SWORDSDANCE'),
('300114', '2067', 'level', '42', 'HAIL'),
('300115', '2067', 'level', '46', 'BLIZZARD'),
('300116', '2067', 'tutor', '0', 'AERIALACE'),
('300117', '2067', 'tutor', '0', 'AMNESIA'),
('300118', '2067', 'tutor', '0', 'AQUATAIL'),
('300119', '2067', 'tutor', '0', 'ATTRACT'),
('300120', '2067', 'tutor', '0', 'AURORAVEIL'),
('300121', '2067', 'tutor', '0', 'AVALANCHE'),
('300122', '2067', 'tutor', '0', 'BLIZZARD'),
('300123', '2067', 'tutor', '0', 'BODYSLAM'),
('300124', '2067', 'tutor', '0', 'BRICKBREAK'),
('300125', '2067', 'tutor', '0', 'BULLDOZE'),
('300126', '2067', 'tutor', '0', 'CAPTIVATE'),
('300127', '2067', 'tutor', '0', 'CONFIDE'),
('300128', '2067', 'tutor', '0', 'COUNTER'),
('300129', '2067', 'tutor', '0', 'COVET'),
('300130', '2067', 'tutor', '0', 'CUT'),
('300131', '2067', 'tutor', '0', 'DEFENSECURL'),
('300132', '2067', 'tutor', '0', 'DIG'),
('300133', '2067', 'tutor', '0', 'DOUBLEEDGE'),
('300134', '2067', 'tutor', '0', 'DOUBLETEAM'),
('300135', '2067', 'tutor', '0', 'DYNAMICPUNCH'),
('300136', '2067', 'tutor', '0', 'EARTHQUAKE'),
('300137', '2067', 'tutor', '0', 'ENDURE'),
('300138', '2067', 'tutor', '0', 'FACADE'),
('300139', '2067', 'tutor', '0', 'FLING'),
('300140', '2067', 'tutor', '0', 'FOCUSPUNCH'),
('300141', '2067', 'tutor', '0', 'FROSTBREATH'),
('300142', '2067', 'tutor', '0', 'FRUSTRATION'),
('300143', '2067', 'tutor', '0', 'FURYCUTTER'),
('300144', '2067', 'tutor', '0', 'GYROBALL'),
('300145', '2067', 'tutor', '0', 'HAIL'),
('300146', '2067', 'tutor', '0', 'HEADBUTT'),
('300147', '2067', 'tutor', '0', 'HIDDENPOWER'),
('300148', '2067', 'tutor', '0', 'HONECLAWS'),
('300149', '2067', 'tutor', '0', 'ICEPUNCH'),
('300150', '2067', 'tutor', '0', 'ICICLESPEAR'),
('300151', '2067', 'tutor', '0', 'ICYWIND'),
('300152', '2067', 'tutor', '0', 'IRONDEFENSE'),
('300153', '2067', 'tutor', '0', 'IRONHEAD'),
('300154', '2067', 'tutor', '0', 'IRONTAIL'),
('300155', '2067', 'tutor', '0', 'KNOCKOFF'),
('300156', '2067', 'tutor', '0', 'LEECHLIFE'),
('300157', '2067', 'tutor', '0', 'MIMIC'),
('300158', '2067', 'tutor', '0', 'NATURALGIFT'),
('300159', '2067', 'tutor', '0', 'POISONJAB'),
('300160', '2067', 'tutor', '0', 'PROTECT'),
('300161', '2067', 'tutor', '0', 'REST'),
('300162', '2067', 'tutor', '0', 'RETURN'),
('300163', '2067', 'tutor', '0', 'ROCKCLIMB'),
('300164', '2067', 'tutor', '0', 'ROCKSLIDE'),
('300165', '2067', 'tutor', '0', 'ROCKSMASH'),
('300166', '2067', 'tutor', '0', 'ROCKTOMB'),
('300167', '2067', 'tutor', '0', 'ROLLOUT'),
('300168', '2067', 'tutor', '0', 'ROUND'),
('300169', '2067', 'tutor', '0', 'SAFEGUARD'),
('300170', '2067', 'tutor', '0', 'SECRETPOWER'),
('300171', '2067', 'tutor', '0', 'SEISMICTOSS'),
('300172', '2067', 'tutor', '0', 'SHADOWCLAW'),
('300173', '2067', 'tutor', '0', 'SLEEPTALK'),
('300174', '2067', 'tutor', '0', 'SNORE'),
('300175', '2067', 'tutor', '0', 'STEALTHROCK'),
('300176', '2067', 'tutor', '0', 'STEELBEAM'),
('300177', '2067', 'tutor', '0', 'STEELROLLER'),
('300178', '2067', 'tutor', '0', 'STRENGTH'),
('300179', '2067', 'tutor', '0', 'SUBSTITUTE'),
('300180', '2067', 'tutor', '0', 'SUNNYDAY'),
('300181', '2067', 'tutor', '0', 'SUPERFANG'),
('300182', '2067', 'tutor', '0', 'SWAGGER'),
('300183', '2067', 'tutor', '0', 'SWIFT'),
('300184', '2067', 'tutor', '0', 'SWORDSDANCE'),
('300185', '2067', 'tutor', '0', 'THIEF'),
('300186', '2067', 'tutor', '0', 'THROATCHOP'),
('300187', '2067', 'tutor', '0', 'TRIPLEAXEL'),
('300188', '2067', 'tutor', '0', 'WORKUP'),
('300189', '2067', 'tutor', '0', 'XSCISSOR'),
('300190', '2068', 'level', '0', 'ICICLESPEAR'),
('300191', '2068', 'level', '1', 'METALBURST'),
('300192', '2068', 'level', '1', 'ICICLECRASH'),
('300193', '2068', 'level', '1', 'SLASH'),
('300194', '2068', 'level', '1', 'DEFENSECURL'),
('300195', '2068', 'level', '1', 'ICEBALL'),
('300196', '2068', 'level', '1', 'METALCLAW'),
('300197', '2068', 'tutor', '0', 'AERIALACE'),
('300198', '2068', 'tutor', '0', 'AGILITY'),
('300199', '2068', 'tutor', '0', 'AMNESIA'),
('300200', '2068', 'tutor', '0', 'AQUATAIL'),
('300201', '2068', 'tutor', '0', 'ATTRACT'),
('300202', '2068', 'tutor', '0', 'AURORAVEIL'),
('300203', '2068', 'tutor', '0', 'AVALANCHE'),
('300204', '2068', 'tutor', '0', 'BLIZZARD'),
('300205', '2068', 'tutor', '0', 'BODYSLAM'),
('300206', '2068', 'tutor', '0', 'BRICKBREAK'),
('300207', '2068', 'tutor', '0', 'BULLDOZE'),
('300208', '2068', 'tutor', '0', 'CAPTIVATE'),
('300209', '2068', 'tutor', '0', 'CONFIDE'),
('300210', '2068', 'tutor', '0', 'COUNTER'),
('300211', '2068', 'tutor', '0', 'COVET'),
('300212', '2068', 'tutor', '0', 'CUT'),
('300213', '2068', 'tutor', '0', 'DEFENSECURL'),
('300214', '2068', 'tutor', '0', 'DIG'),
('300215', '2068', 'tutor', '0', 'DOUBLEEDGE'),
('300216', '2068', 'tutor', '0', 'DOUBLETEAM'),
('300217', '2068', 'tutor', '0', 'DYNAMICPUNCH'),
('300218', '2068', 'tutor', '0', 'DRILLRUN'),
('300219', '2068', 'tutor', '0', 'EARTHQUAKE'),
('300220', '2068', 'tutor', '0', 'ENDURE'),
('300221', '2068', 'tutor', '0', 'FACADE'),
('300222', '2068', 'tutor', '0', 'FLING'),
('300223', '2068', 'tutor', '0', 'FOCUSBLAST'),
('300224', '2068', 'tutor', '0', 'FOCUSPUNCH'),
('300225', '2068', 'tutor', '0', 'FROSTBREATH'),
('300226', '2068', 'tutor', '0', 'FRUSTRATION'),
('300227', '2068', 'tutor', '0', 'FURYCUTTER'),
('300228', '2068', 'tutor', '0', 'GIGAIMPACT'),
('300229', '2068', 'tutor', '0', 'GYROBALL'),
('300230', '2068', 'tutor', '0', 'HAIL'),
('300231', '2068', 'tutor', '0', 'HEADBUTT'),
('300232', '2068', 'tutor', '0', 'HIDDENPOWER'),
('300233', '2068', 'tutor', '0', 'HONECLAWS'),
('300234', '2068', 'tutor', '0', 'HYPERBEAM'),
('300235', '2068', 'tutor', '0', 'ICEPUNCH'),
('300236', '2068', 'tutor', '0', 'ICYWIND'),
('300237', '2068', 'tutor', '0', 'IRONDEFENSE'),
('300238', '2068', 'tutor', '0', 'IRONHEAD'),
('300239', '2068', 'tutor', '0', 'IRONTAIL'),
('300240', '2068', 'tutor', '0', 'KNOCKOFF'),
('300241', '2068', 'tutor', '0', 'LEECHLIFE'),
('300242', '2068', 'tutor', '0', 'MIMIC'),
('300243', '2068', 'tutor', '0', 'NATURALGIFT'),
('300244', '2068', 'tutor', '0', 'PINMISSILE'),
('300245', '2068', 'tutor', '0', 'POISONJAB'),
('300246', '2068', 'tutor', '0', 'PROTECT'),
('300247', '2068', 'tutor', '0', 'REST'),
('300248', '2068', 'tutor', '0', 'RETURN'),
('300249', '2068', 'tutor', '0', 'ROCKCLIMB'),
('300250', '2068', 'tutor', '0', 'ROCKSLIDE'),
('300251', '2068', 'tutor', '0', 'ROCKSMASH'),
('300252', '2068', 'tutor', '0', 'ROCKTOMB'),
('300253', '2068', 'tutor', '0', 'ROLLOUT'),
('300254', '2068', 'tutor', '0', 'ROUND'),
('300255', '2068', 'tutor', '0', 'SAFEGUARD'),
('300256', '2068', 'tutor', '0', 'SECRETPOWER'),
('300257', '2068', 'tutor', '0', 'SEISMICTOSS'),
('300258', '2068', 'tutor', '0', 'SHADOWCLAW'),
('300259', '2068', 'tutor', '0', 'SLEEPTALK'),
('300260', '2068', 'tutor', '0', 'SNORE'),
('300261', '2068', 'tutor', '0', 'SPIKES'),
('300262', '2068', 'tutor', '0', 'STEALTHROCK'),
('300263', '2068', 'tutor', '0', 'STEELBEAM'),
('300264', '2068', 'tutor', '0', 'STEELROLLER'),
('300265', '2068', 'tutor', '0', 'STRENGTH'),
('300266', '2068', 'tutor', '0', 'SUBSTITUTE'),
('300267', '2068', 'tutor', '0', 'SUNNYDAY'),
('300268', '2068', 'tutor', '0', 'SUPERFANG'),
('300269', '2068', 'tutor', '0', 'SWAGGER'),
('300270', '2068', 'tutor', '0', 'SWIFT'),
('300271', '2068', 'tutor', '0', 'SWORDSDANCE'),
('300272', '2068', 'tutor', '0', 'THIEF'),
('300273', '2068', 'tutor', '0', 'THROATCHOP'),
('300274', '2068', 'tutor', '0', 'TRIPLEAXEL'),
('300275', '2068', 'tutor', '0', 'WORKUP'),
('300276', '2068', 'tutor', '0', 'XSCISSOR'),
('300277', '2081', 'level', '1', 'POWDERSNOW'),
('300278', '2081', 'level', '4', 'TAILWHIP'),
('300279', '2081', 'level', '7', 'ROAR'),
('300280', '2081', 'level', '9', 'BABYDOLLEYES'),
('300281', '2081', 'level', '10', 'ICESHARD'),
('300282', '2081', 'level', '12', 'CONFUSERAY'),
('300283', '2081', 'level', '15', 'ICYWIND'),
('300284', '2081', 'level', '18', 'PAYBACK'),
('300285', '2081', 'level', '20', 'MIST'),
('300286', '2081', 'level', '23', 'FEINTATTACK'),
('300287', '2081', 'level', '26', 'HEX'),
('300288', '2081', 'level', '28', 'AURORABEAM'),
('300289', '2081', 'level', '31', 'EXTRASENSORY'),
('300290', '2081', 'level', '34', 'SAFEGUARD'),
('300291', '2081', 'level', '36', 'ICEBEAM'),
('300292', '2081', 'level', '39', 'IMPRISON'),
('300293', '2081', 'level', '42', 'BLIZZARD'),
('300294', '2081', 'level', '44', 'GRUDGE'),
('300295', '2081', 'level', '47', 'CAPTIVATE'),
('300296', '2081', 'level', '50', 'SHEERCOLD'),
('300297', '2081', 'tutor', '0', 'AGILITY'),
('300298', '2081', 'tutor', '0', 'AQUATAIL'),
('300299', '2081', 'tutor', '0', 'ATTRACT'),
('300300', '2081', 'tutor', '0', 'AURORAVEIL'),
('300301', '2081', 'tutor', '0', 'BLIZZARD'),
('300302', '2081', 'tutor', '0', 'BODYSLAM'),
('300303', '2081', 'tutor', '0', 'CAPTIVATE'),
('300304', '2081', 'tutor', '0', 'CHARM'),
('300305', '2081', 'tutor', '0', 'CONFIDE'),
('300306', '2081', 'tutor', '0', 'COVET'),
('300307', '2081', 'tutor', '0', 'DARKPULSE'),
('300308', '2081', 'tutor', '0', 'DIG'),
('300309', '2081', 'tutor', '0', 'DOUBLEEDGE'),
('300310', '2081', 'tutor', '0', 'DOUBLETEAM'),
('300311', '2081', 'tutor', '0', 'DRAININGKISS'),
('300312', '2081', 'tutor', '0', 'ENCORE'),
('300313', '2081', 'tutor', '0', 'ENDURE'),
('300314', '2081', 'tutor', '0', 'FACADE'),
('300315', '2081', 'tutor', '0', 'FOULPLAY'),
('300316', '2081', 'tutor', '0', 'FROSTBREATH'),
('300317', '2081', 'tutor', '0', 'FRUSTRATION'),
('300318', '2081', 'tutor', '0', 'HAIL'),
('300319', '2081', 'tutor', '0', 'HEADBUTT'),
('300320', '2081', 'tutor', '0', 'HEALBELL'),
('300321', '2081', 'tutor', '0', 'HEX'),
('300322', '2081', 'tutor', '0', 'HIDDENPOWER'),
('300323', '2081', 'tutor', '0', 'ICEBEAM'),
('300324', '2081', 'tutor', '0', 'ICYWIND'),
('300325', '2081', 'tutor', '0', 'IMPRISON'),
('300326', '2081', 'tutor', '0', 'IRONTAIL'),
('300327', '2081', 'tutor', '0', 'MIMIC'),
('300328', '2081', 'tutor', '0', 'NATURALGIFT'),
('300329', '2081', 'tutor', '0', 'PAINSPLIT'),
('300330', '2081', 'tutor', '0', 'PAYBACK'),
('300331', '2081', 'tutor', '0', 'POWERSWAP'),
('300332', '2081', 'tutor', '0', 'PROTECT'),
('300333', '2081', 'tutor', '0', 'PSYCHUP'),
('300334', '2081', 'tutor', '0', 'RAINDANCE'),
('300335', '2081', 'tutor', '0', 'REST'),
('300336', '2081', 'tutor', '0', 'RETURN'),
('300337', '2081', 'tutor', '0', 'ROAR'),
('300338', '2081', 'tutor', '0', 'ROLEPLAY'),
('300339', '2081', 'tutor', '0', 'ROUND'),
('300340', '2081', 'tutor', '0', 'SAFEGUARD'),
('300341', '2081', 'tutor', '0', 'SECRETPOWER'),
('300342', '2081', 'tutor', '0', 'SLEEPTALK'),
('300343', '2081', 'tutor', '0', 'SNORE'),
('300344', '2081', 'tutor', '0', 'SPITE'),
('300345', '2081', 'tutor', '0', 'SUBSTITUTE'),
('300346', '2081', 'tutor', '0', 'SWAGGER'),
('300347', '2081', 'tutor', '0', 'SWIFT'),
('300348', '2081', 'tutor', '0', 'TAILSLAP'),
('300349', '2081', 'tutor', '0', 'WEATHERBALL'),
('300350', '2081', 'tutor', '0', 'ZENHEADBUTT'),
('300351', '2083', 'level', '0', 'DAZZLINGGLEAM'),
('300352', '2083', 'level', '1', 'IMPRISON'),
('300353', '2083', 'level', '1', 'NASTYPLOT'),
('300354', '2083', 'level', '1', 'ICEBEAM'),
('300355', '2083', 'level', '1', 'ICESHARD'),
('300356', '2083', 'level', '1', 'CONFUSERAY'),
('300357', '2083', 'level', '1', 'SAFEGUARD'),
('300358', '2083', 'tutor', '0', 'AGILITY'),
('300359', '2083', 'tutor', '0', 'AQUATAIL'),
('300360', '2083', 'tutor', '0', 'ATTRACT'),
('300361', '2083', 'tutor', '0', 'AURORAVEIL'),
('300362', '2083', 'tutor', '0', 'AVALANCHE'),
('300363', '2083', 'tutor', '0', 'BLIZZARD'),
('300364', '2083', 'tutor', '0', 'BODYSLAM'),
('300365', '2083', 'tutor', '0', 'CALMMIND'),
('300366', '2083', 'tutor', '0', 'CAPTIVATE'),
('300367', '2083', 'tutor', '0', 'CHARM'),
('300368', '2083', 'tutor', '0', 'CONFIDE'),
('300369', '2083', 'tutor', '0', 'COVET'),
('300370', '2083', 'tutor', '0', 'DARKPULSE'),
('300371', '2083', 'tutor', '0', 'DAZZLINGGLEAM'),
('300372', '2083', 'tutor', '0', 'DIG'),
('300373', '2083', 'tutor', '0', 'DOUBLEEDGE'),
('300374', '2083', 'tutor', '0', 'DOUBLETEAM'),
('300375', '2083', 'tutor', '0', 'DRAININGKISS'),
('300376', '2083', 'tutor', '0', 'DREAMEATER'),
('300377', '2083', 'tutor', '0', 'ENCORE'),
('300378', '2083', 'tutor', '0', 'ENDURE'),
('300379', '2083', 'tutor', '0', 'FACADE'),
('300380', '2083', 'tutor', '0', 'FAKETEARS'),
('300381', '2083', 'tutor', '0', 'FOULPLAY'),
('300382', '2083', 'tutor', '0', 'FROSTBREATH'),
('300383', '2083', 'tutor', '0', 'FRUSTRATION'),
('300384', '2083', 'tutor', '0', 'GIGAIMPACT'),
('300385', '2083', 'tutor', '0', 'HAIL'),
('300386', '2083', 'tutor', '0', 'HEADBUTT'),
('300387', '2083', 'tutor', '0', 'HEALBELL'),
('300388', '2083', 'tutor', '0', 'HEX'),
('300389', '2083', 'tutor', '0', 'HIDDENPOWER'),
('300390', '2083', 'tutor', '0', 'HYPERBEAM'),
('300391', '2083', 'tutor', '0', 'ICEBEAM'),
('300392', '2083', 'tutor', '0', 'ICYWIND'),
('300393', '2083', 'tutor', '0', 'IMPRISON'),
('300394', '2083', 'tutor', '0', 'IRONTAIL'),
('300395', '2083', 'tutor', '0', 'LASERFOCUS'),
('300396', '2083', 'tutor', '0', 'MIMIC'),
('300397', '2083', 'tutor', '0', 'MISTYTERRAIN'),
('300398', '2083', 'tutor', '0', 'NASTYPLOT'),
('300399', '2083', 'tutor', '0', 'NATURALGIFT'),
('300400', '2083', 'tutor', '0', 'PAINSPLIT'),
('300401', '2083', 'tutor', '0', 'PAYBACK'),
('300402', '2083', 'tutor', '0', 'POWERSWAP'),
('300403', '2083', 'tutor', '0', 'PROTECT'),
('300404', '2083', 'tutor', '0', 'PSYCHUP'),
('300405', '2083', 'tutor', '0', 'PSYSHOCK'),
('300406', '2083', 'tutor', '0', 'RAINDANCE'),
('300407', '2083', 'tutor', '0', 'REST'),
('300408', '2083', 'tutor', '0', 'RETURN'),
('300409', '2083', 'tutor', '0', 'ROAR'),
('300410', '2083', 'tutor', '0', 'ROLEPLAY'),
('300411', '2083', 'tutor', '0', 'ROUND'),
('300412', '2083', 'tutor', '0', 'SAFEGUARD'),
('300413', '2083', 'tutor', '0', 'SECRETPOWER'),
('300414', '2083', 'tutor', '0', 'SLEEPTALK'),
('300415', '2083', 'tutor', '0', 'SNORE'),
('300416', '2083', 'tutor', '0', 'SOLARBEAM'),
('300417', '2083', 'tutor', '0', 'SPITE'),
('300418', '2083', 'tutor', '0', 'STOREDPOWER'),
('300419', '2083', 'tutor', '0', 'SUBSTITUTE'),
('300420', '2083', 'tutor', '0', 'SWAGGER'),
('300421', '2083', 'tutor', '0', 'SWIFT'),
('300422', '2083', 'tutor', '0', 'TAILSLAP'),
('300423', '2083', 'tutor', '0', 'TRIPLEAXEL'),
('300424', '2083', 'tutor', '0', 'WEATHERBALL'),
('300425', '2083', 'tutor', '0', 'WONDERROOM'),
('300426', '2083', 'tutor', '0', 'ZENHEADBUTT'),
('300427', '2286', 'level', '1', 'PECK'),
('300428', '2286', 'level', '1', 'FOCUSENERGY'),
('300429', '2286', 'level', '5', 'ROCKSMASH'),
('300430', '2286', 'level', '10', 'LIGHTSCREEN'),
('300431', '2286', 'level', '15', 'PLUCK'),
('300432', '2286', 'level', '20', 'AGILITY'),
('300433', '2286', 'level', '25', 'ANCIENTPOWER'),
('300434', '2286', 'level', '30', 'BRICKBREAK'),
('300435', '2286', 'level', '35', 'DRILLPECK'),
('300436', '2286', 'level', '40', 'QUICKGUARD'),
('300437', '2286', 'level', '45', 'THUNDEROUSKICK'),
('300438', '2286', 'level', '50', 'BULKUP'),
('300439', '2286', 'level', '55', 'COUNTER'),
('300440', '2286', 'level', '60', 'DETECT'),
('300441', '2286', 'level', '65', 'CLOSECOMBAT'),
('300442', '2286', 'level', '70', 'REVERSAL'),
('300443', '2286', 'tutor', '0', 'ACROBATICS'),
('300444', '2286', 'tutor', '0', 'AGILITY'),
('300445', '2286', 'tutor', '0', 'ASSURANCE'),
('300446', '2286', 'tutor', '0', 'BLAZEKICK'),
('300447', '2286', 'tutor', '0', 'BOUNCE'),
('300448', '2286', 'tutor', '0', 'BRAVEBIRD'),
('300449', '2286', 'tutor', '0', 'BRICKBREAK'),
('300450', '2286', 'tutor', '0', 'BULKUP'),
('300451', '2286', 'tutor', '0', 'CLOSECOMBAT'),
('300452', '2286', 'tutor', '0', 'COACHING'),
('300453', '2286', 'tutor', '0', 'CONFIDE'),
('300454', '2286', 'tutor', '0', 'DOUBLEEDGE'),
('300455', '2286', 'tutor', '0', 'DOUBLETEAM'),
('300456', '2286', 'tutor', '0', 'DUALWINGBEAT'),
('300457', '2286', 'tutor', '0', 'ENDURE'),
('300458', '2286', 'tutor', '0', 'FACADE'),
('300459', '2286', 'tutor', '0', 'FLY'),
('300460', '2286', 'tutor', '0', 'FOCUSENERGY'),
('300461', '2286', 'tutor', '0', 'FRUSTRATION'),
('300462', '2286', 'tutor', '0', 'GIGAIMPACT'),
('300463', '2286', 'tutor', '0', 'HIDDENPOWER'),
('300464', '2286', 'tutor', '0', 'HURRICANE'),
('300465', '2286', 'tutor', '0', 'HYPERBEAM'),
('300466', '2286', 'tutor', '0', 'LIGHTSCREEN'),
('300467', '2286', 'tutor', '0', 'LOWKICK'),
('300468', '2286', 'tutor', '0', 'LOWSWEEP'),
('300469', '2286', 'tutor', '0', 'MEGAKICK'),
('300470', '2286', 'tutor', '0', 'MIMIC'),
('300471', '2286', 'tutor', '0', 'NATURALGIFT'),
('300472', '2286', 'tutor', '0', 'PAYBACK'),
('300473', '2286', 'tutor', '0', 'PROTECT'),
('300474', '2286', 'tutor', '0', 'REST'),
('300475', '2286', 'tutor', '0', 'RETALIATE'),
('300476', '2286', 'tutor', '0', 'RETURN'),
('300477', '2286', 'tutor', '0', 'REVENGE'),
('300478', '2286', 'tutor', '0', 'REVERSAL'),
('300479', '2286', 'tutor', '0', 'ROUND'),
('300480', '2286', 'tutor', '0', 'SCARYFACE'),
('300481', '2286', 'tutor', '0', 'SCREECH'),
('300482', '2286', 'tutor', '0', 'SECRETPOWER'),
('300483', '2286', 'tutor', '0', 'SLEEPTALK'),
('300484', '2286', 'tutor', '0', 'SNORE'),
('300485', '2286', 'tutor', '0', 'STEELWING'),
('300486', '2286', 'tutor', '0', 'STOMPINGTANTRUM'),
('300487', '2286', 'tutor', '0', 'SUBSTITUTE'),
('300488', '2286', 'tutor', '0', 'SUPERPOWER'),
('300489', '2286', 'tutor', '0', 'SWAGGER'),
('300490', '2286', 'tutor', '0', 'SWIFT'),
('300491', '2286', 'tutor', '0', 'TAUNT'),
('300492', '2286', 'tutor', '0', 'THROATCHOP'),
('300493', '2286', 'tutor', '0', 'UTURN'),
('300494', '2292', 'level', '1', 'GUST'),
('300495', '2292', 'level', '1', 'LEER'),
('300496', '2292', 'level', '5', 'PAYBACK'),
('300497', '2292', 'level', '10', 'SAFEGUARD'),
('300498', '2292', 'level', '15', 'WINGATTACK'),
('300499', '2292', 'level', '20', 'AGILITY'),
('300500', '2292', 'level', '25', 'ANCIENTPOWER'),
('300501', '2292', 'level', '30', 'SUCKERPUNCH'),
('300502', '2292', 'level', '35', 'AIRSLASH'),
('300503', '2292', 'level', '40', 'AFTERYOU'),
('300504', '2292', 'level', '45', 'FIERYWRATH'),
('300505', '2292', 'level', '50', 'NASTYPLOT'),
('300506', '2292', 'level', '55', 'HURRICANE'),
('300507', '2292', 'level', '60', 'ENDURE'),
('300508', '2292', 'level', '65', 'MEMENTO'),
('300509', '2292', 'level', '70', 'SKYATTACK'),
('300510', '2292', 'tutor', '0', 'AGILITY'),
('300511', '2292', 'tutor', '0', 'AIRSLASH'),
('300512', '2292', 'tutor', '0', 'ASSURANCE'),
('300513', '2292', 'tutor', '0', 'BRAVEBIRD'),
('300514', '2292', 'tutor', '0', 'CONFIDE'),
('300515', '2292', 'tutor', '0', 'DARKPULSE'),
('300516', '2292', 'tutor', '0', 'DOUBLEEDGE'),
('300517', '2292', 'tutor', '0', 'DOUBLETEAM'),
('300518', '2292', 'tutor', '0', 'DUALWINGBEAT'),
('300519', '2292', 'tutor', '0', 'ENDURE'),
('300520', '2292', 'tutor', '0', 'FACADE'),
('300521', '2292', 'tutor', '0', 'FLY'),
('300522', '2292', 'tutor', '0', 'FOULPLAY'),
('300523', '2292', 'tutor', '0', 'FRUSTRATION'),
('300524', '2292', 'tutor', '0', 'GIGAIMPACT'),
('300525', '2292', 'tutor', '0', 'HEX'),
('300526', '2292', 'tutor', '0', 'HIDDENPOWER'),
('300527', '2292', 'tutor', '0', 'HURRICANE'),
('300528', '2292', 'tutor', '0', 'HYPERBEAM'),
('300529', '2292', 'tutor', '0', 'HYPERVOICE'),
('300530', '2292', 'tutor', '0', 'IMPRISON'),
('300531', '2292', 'tutor', '0', 'LASHOUT'),
('300532', '2292', 'tutor', '0', 'MIMIC'),
('300533', '2292', 'tutor', '0', 'NASTYPLOT'),
('300534', '2292', 'tutor', '0', 'NATURALGIFT'),
('300535', '2292', 'tutor', '0', 'PAYBACK'),
('300536', '2292', 'tutor', '0', 'PROTECT'),
('300537', '2292', 'tutor', '0', 'REST'),
('300538', '2292', 'tutor', '0', 'RETURN'),
('300539', '2292', 'tutor', '0', 'ROUND'),
('300540', '2292', 'tutor', '0', 'SAFEGUARD'),
('300541', '2292', 'tutor', '0', 'SCARYFACE'),
('300542', '2292', 'tutor', '0', 'SECRETPOWER'),
('300543', '2292', 'tutor', '0', 'SHADOWBALL'),
('300544', '2292', 'tutor', '0', 'SLEEPTALK'),
('300545', '2292', 'tutor', '0', 'SNARL'),
('300546', '2292', 'tutor', '0', 'SNORE'),
('300547', '2292', 'tutor', '0', 'STEELWING'),
('300548', '2292', 'tutor', '0', 'SUBSTITUTE'),
('300549', '2292', 'tutor', '0', 'SWAGGER'),
('300550', '2292', 'tutor', '0', 'SWIFT'),
('300551', '2292', 'tutor', '0', 'TAUNT'),
('300552', '2292', 'tutor', '0', 'UTURN'),
('300553', '2557', 'level', '1', 'GROWTH'),
('300554', '2557', 'level', '10', 'MAGICALLEAF'),
('300555', '2557', 'level', '19', 'LEECHSEED'),
('300556', '2557', 'level', '28', 'QUICKATTACK'),
('300557', '2557', 'level', '37', 'SWEETSCENT'),
('300558', '2557', 'level', '46', 'HEALINGWISH'),
('300559', '2557', 'level', '55', 'WORRYSEED'),
('300560', '2557', 'level', '64', 'AIRSLASH'),
('300561', '2557', 'level', '73', 'ENERGYBALL'),
('300562', '2557', 'level', '82', 'SWEETKISS'),
('300563', '2557', 'level', '91', 'LEAFSTORM'),
('300564', '2557', 'level', '100', 'SEEDFLARE'),
('300565', '2557', 'tutor', '0', 'AIRCUTTER'),
('300566', '2557', 'tutor', '0', 'BULLETSEED'),
('300567', '2557', 'tutor', '0', 'CONFIDE'),
('300568', '2557', 'tutor', '0', 'COVET'),
('300569', '2557', 'tutor', '0', 'DAZZLINGGLEAM'),
('300570', '2557', 'tutor', '0', 'DOUBLEEDGE'),
('300571', '2557', 'tutor', '0', 'DOUBLETEAM'),
('300572', '2557', 'tutor', '0', 'ENDURE'),
('300573', '2557', 'tutor', '0', 'ENERGYBALL'),
('300574', '2557', 'tutor', '0', 'FACADE'),
('300575', '2557', 'tutor', '0', 'FLASH'),
('300576', '2557', 'tutor', '0', 'FRUSTRATION'),
('300577', '2557', 'tutor', '0', 'GIGADRAIN'),
('300578', '2557', 'tutor', '0', 'GIGAIMPACT'),
('300579', '2557', 'tutor', '0', 'GRASSKNOT'),
('300580', '2557', 'tutor', '0', 'HEADBUTT'),
('300581', '2557', 'tutor', '0', 'HIDDENPOWER'),
('300582', '2557', 'tutor', '0', 'HYPERBEAM'),
('300583', '2557', 'tutor', '0', 'LASERFOCUS'),
('300584', '2557', 'tutor', '0', 'LASTRESORT'),
('300585', '2557', 'tutor', '0', 'MIMIC'),
('300586', '2557', 'tutor', '0', 'MUDSLAP'),
('300587', '2557', 'tutor', '0', 'NATURALGIFT'),
('300588', '2557', 'tutor', '0', 'NATUREPOWER'),
('300589', '2557', 'tutor', '0', 'OMINOUSWIND'),
('300590', '2557', 'tutor', '0', 'PROTECT'),
('300591', '2557', 'tutor', '0', 'PSYCHIC'),
('300592', '2557', 'tutor', '0', 'PSYCHUP'),
('300593', '2557', 'tutor', '0', 'REST'),
('300594', '2557', 'tutor', '0', 'RETURN'),
('300595', '2557', 'tutor', '0', 'ROUND'),
('300596', '2557', 'tutor', '0', 'SAFEGUARD'),
('300597', '2557', 'tutor', '0', 'SECRETPOWER'),
('300598', '2557', 'tutor', '0', 'SEEDBOMB'),
('300599', '2557', 'tutor', '0', 'SLEEPTALK'),
('300600', '2557', 'tutor', '0', 'SNORE'),
('300601', '2557', 'tutor', '0', 'SOLARBEAM'),
('300602', '2557', 'tutor', '0', 'SUBSTITUTE'),
('300603', '2557', 'tutor', '0', 'SUNNYDAY'),
('300604', '2557', 'tutor', '0', 'SWAGGER'),
('300605', '2557', 'tutor', '0', 'SWIFT'),
('300606', '2557', 'tutor', '0', 'SWORDSDANCE'),
('300607', '2557', 'tutor', '0', 'SYNTHESIS'),
('300608', '2557', 'tutor', '0', 'TAILWIND'),
('300609', '2557', 'tutor', '0', 'WORRYSEED'),
('300610', '2557', 'tutor', '0', 'ZENHEADBUTT'),
('300611', '2974', 'level', '1', 'LEER'),
('300612', '2974', 'level', '1', 'SCRATCH'),
('300613', '2974', 'level', '3', 'LEAFAGE'),
('300614', '2974', 'level', '7', 'SANDATTACK'),
('300615', '2974', 'level', '12', 'PECK'),
('300616', '2974', 'level', '16', 'RAZORLEAF'),
('300617', '2974', 'level', '20', 'WINGATTACK'),
('300618', '2974', 'level', '25', 'FAKEOUT'),
('300619', '2974', 'level', '32', 'AIRCUTTER'),
('300620', '2974', 'level', '36', 'LEAFBLADE'),
('300621', '2974', 'level', '40', 'SYNTHESIS'),
('300622', '2976', 'level', '1', 'GROWL'),
('300623', '2976', 'level', '1', 'TACKLE'),
('300624', '2976', 'level', '3', 'EMBER'),
('300625', '2976', 'level', '7', 'BITE'),
('300626', '2976', 'level', '12', 'BABYDOLLEYES'),
('300627', '2976', 'level', '16', 'FLAMECHARGE'),
('300628', '2976', 'level', '20', 'TAKEDOWN'),
('300629', '2976', 'level', '25', 'ROAR'),
('300630', '2976', 'level', '32', 'FIREFANG'),
('300631', '2976', 'level', '36', 'CRUNCH'),
('300632', '2976', 'level', '40', 'HEATWAVE'),
('300633', '2978', 'level', '1', 'POUND'),
('300634', '2978', 'level', '1', 'TAILWHIP'),
('300635', '2978', 'level', '3', 'WATERGUN'),
('300636', '2978', 'level', '7', 'LICK'),
('300637', '2978', 'level', '12', 'CAMOUFLAGE'),
('300638', '2978', 'level', '16', 'WATERPULSE'),
('300639', '2978', 'level', '20', 'FAKETEARS'),
('300640', '2978', 'level', '25', 'AQUATAIL'),
('300641', '2978', 'level', '32', 'SUBSTITUTE'),
('300642', '2978', 'level', '36', 'AQUARING'),
('300643', '2978', 'level', '40', 'HYDROPUMP');

CREATE TEMPORARY TABLE `bm3d_creature` LIKE `creature_template`;
COMMIT;
DROP PROCEDURE IF EXISTS `bm3d_templates`;
DELIMITER //
CREATE PROCEDURE `bm3d_templates`()
BEGIN
    DECLARE finished INT DEFAULT 0;
    DECLARE fid INT UNSIGNED;
    DECLARE fname VARCHAR(255);
    DECLARE forms_cursor CURSOR FOR SELECT `id`,`name` FROM `bm3d_forms`;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET finished=1;
    OPEN forms_cursor;
    forms_loop: LOOP
        FETCH forms_cursor INTO fid, fname;
        IF finished=1 THEN LEAVE forms_loop; END IF;
        DELETE FROM `bm3d_creature`;
        INSERT INTO `bm3d_creature` SELECT * FROM `creature_template` WHERE `entry`=60000;
        UPDATE `bm3d_creature` SET `entry`=1000000+fid, `name`=fname;
        DELETE FROM `creature_template` WHERE `entry`=1000000+fid;
        INSERT INTO `creature_template` SELECT * FROM `bm3d_creature`;
    END LOOP;
    CLOSE forms_cursor;
END//
DELIMITER ;
START TRANSACTION;
CALL `bm3d_templates`();
DELETE FROM `creature_template_model` WHERE `CreatureID`=1000544;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1000544', '0', '400454', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1000675;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1000675', '0', '400532', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1000738;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1000738', '0', '400552', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1000840;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1000840', '0', '400567', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1000841;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1000841', '0', '400565', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1000904;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1000904', '0', '400597', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1000918;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1000918', '0', '400599', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1001160;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1001160', '0', '400639', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002000;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002000', '0', '400000', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002001;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002001', '0', '400001', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002002;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002002', '0', '400002', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002003;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002003', '0', '400003', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002005;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002005', '0', '400005', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002006;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002006', '0', '400006', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002008;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002008', '0', '400008', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002010;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002010', '0', '400010', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002011;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002011', '0', '400011', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002014;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002014', '0', '400014', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002015;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002015', '0', '400015', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002016;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002016', '0', '400016', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002018;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002018', '0', '400018', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002019;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002019', '0', '400019', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002020;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002020', '0', '400020', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002022;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002022', '0', '400022', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002023;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002023', '0', '400023', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002024;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002024', '0', '400024', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002025;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002025', '0', '400025', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002026;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002026', '0', '400026', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002027;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002027', '0', '400027', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002028;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002028', '0', '400028', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002029;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002029', '0', '400029', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002030;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002030', '0', '400030', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002031;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002031', '0', '400031', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002032;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002032', '0', '400032', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002034;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002034', '0', '400034', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002035;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002035', '0', '400035', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002036;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002036', '0', '400036', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002037;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002037', '0', '400037', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002038;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002038', '0', '400038', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002039;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002039', '0', '400039', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002040;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002040', '0', '400040', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002042;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002042', '0', '400042', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002043;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002043', '0', '400043', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002044;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002044', '0', '400044', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002046;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002046', '0', '400046', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002047;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002047', '0', '400047', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002048;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002048', '0', '400048', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002050;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002050', '0', '400050', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002051;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002051', '0', '400051', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002052;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002052', '0', '400052', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002053;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002053', '0', '400053', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002054;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002054', '0', '400054', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002056;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002056', '0', '400056', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002057;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002057', '0', '400057', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002058;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002058', '0', '400058', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002059;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002059', '0', '400059', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002060;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002060', '0', '400060', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002061;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002061', '0', '400061', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002062;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002062', '0', '400062', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002064;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002064', '0', '400064', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002065;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002065', '0', '400065', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002066;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002066', '0', '400066', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002067;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002067', '0', '400067', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002068;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002068', '0', '400068', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002069;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002069', '0', '400069', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002070;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002070', '0', '400070', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002071;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002071', '0', '400071', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002072;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002072', '0', '400072', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002073;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002073', '0', '400073', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002074;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002074', '0', '400074', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002075;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002075', '0', '400075', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002076;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002076', '0', '400076', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002077;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002077', '0', '400077', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002078;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002078', '0', '400078', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002079;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002079', '0', '400079', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002080;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002080', '0', '400080', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002081;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002081', '0', '400081', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002082;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002082', '0', '400082', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002083;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002083', '0', '400083', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002084;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002084', '0', '400084', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002085;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002085', '0', '400085', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002086;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002086', '0', '400086', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002087;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002087', '0', '400087', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002088;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002088', '0', '400088', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002089;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002089', '0', '400089', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002090;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002090', '0', '400090', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002091;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002091', '0', '400091', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002092;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002092', '0', '400092', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002093;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002093', '0', '400093', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002094;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002094', '0', '400094', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002095;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002095', '0', '400095', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002096;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002096', '0', '400096', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002097;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002097', '0', '400097', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002098;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002098', '0', '400098', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002099;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002099', '0', '400099', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002100;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002100', '0', '400100', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002101;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002101', '0', '400101', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002103;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002103', '0', '400103', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002104;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002104', '0', '400104', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002105;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002105', '0', '400105', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002106;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002106', '0', '400106', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002107;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002107', '0', '400107', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002108;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002108', '0', '400108', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002109;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002109', '0', '400109', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002110;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002110', '0', '400110', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002111;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002111', '0', '400111', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002113;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002113', '0', '400113', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002114;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002114', '0', '400114', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002115;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002115', '0', '400115', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002116;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002116', '0', '400116', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002117;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002117', '0', '400117', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002118;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002118', '0', '400118', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002119;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002119', '0', '400119', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002120;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002120', '0', '400120', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002121;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002121', '0', '400121', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002122;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002122', '0', '400122', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002123;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002123', '0', '400123', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002124;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002124', '0', '400124', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002125;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002125', '0', '400125', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002126;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002126', '0', '400126', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002127;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002127', '0', '400127', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002128;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002128', '0', '400128', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002129;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002129', '0', '400129', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002130;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002130', '0', '400130', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002131;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002131', '0', '400131', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002132;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002132', '0', '400132', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002133;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002133', '0', '400133', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002135;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002135', '0', '400135', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002136;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002136', '0', '400136', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002138;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002138', '0', '400138', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002139;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002139', '0', '400139', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002140;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002140', '0', '400140', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002141;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002141', '0', '400141', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002142;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002142', '0', '400142', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002143;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002143', '0', '400143', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002144;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002144', '0', '400144', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002145;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002145', '0', '400145', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002146;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002146', '0', '400146', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002147;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002147', '0', '400147', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002148;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002148', '0', '400148', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002149;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002149', '0', '400149', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002150;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002150', '0', '400150', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002151;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002151', '0', '400151', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002152;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002152', '0', '400152', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002153;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002153', '0', '400153', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002154;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002154', '0', '400154', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002155;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002155', '0', '400155', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002156;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002156', '0', '400156', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002157;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002157', '0', '400157', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002158;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002158', '0', '400158', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002159;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002159', '0', '400159', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002160;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002160', '0', '400160', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002161;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002161', '0', '400161', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002162;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002162', '0', '400162', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002163;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002163', '0', '400163', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002164;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002164', '0', '400164', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002165;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002165', '0', '400165', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002166;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002166', '0', '400166', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002167;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002167', '0', '400167', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002168;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002168', '0', '400168', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002169;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002169', '0', '400169', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002170;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002170', '0', '400170', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002171;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002171', '0', '400171', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002172;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002172', '0', '400172', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002173;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002173', '0', '400173', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002174;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002174', '0', '400174', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002175;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002175', '0', '400175', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002176;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002176', '0', '400176', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002177;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002177', '0', '400177', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002178;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002178', '0', '400178', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002179;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002179', '0', '400179', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002180;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002180', '0', '400180', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002181;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002181', '0', '400181', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002182;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002182', '0', '400182', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002183;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002183', '0', '400183', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002184;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002184', '0', '400184', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002185;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002185', '0', '400185', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002186;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002186', '0', '400186', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002187;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002187', '0', '400187', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002188;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002188', '0', '400188', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002189;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002189', '0', '400189', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002190;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002190', '0', '400190', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002191;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002191', '0', '400191', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002192;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002192', '0', '400192', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002193;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002193', '0', '400193', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002194;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002194', '0', '400194', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002195;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002195', '0', '400195', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002196;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002196', '0', '400196', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002197;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002197', '0', '400197', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002198;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002198', '0', '400198', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002199;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002199', '0', '400199', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002200;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002200', '0', '400200', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002201;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002201', '0', '400201', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002202;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002202', '0', '400202', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002203;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002203', '0', '400203', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002204;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002204', '0', '400204', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002205;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002205', '0', '400205', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002206;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002206', '0', '400206', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002207;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002207', '0', '400207', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002208;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002208', '0', '400208', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002209;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002209', '0', '400209', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002210;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002210', '0', '400210', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002211;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002211', '0', '400211', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002212;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002212', '0', '400212', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002213;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002213', '0', '400213', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002214;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002214', '0', '400214', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002215;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002215', '0', '400215', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002216;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002216', '0', '400216', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002217;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002217', '0', '400217', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002218;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002218', '0', '400218', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002219;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002219', '0', '400219', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002220;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002220', '0', '400220', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002221;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002221', '0', '400221', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002222;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002222', '0', '400222', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002223;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002223', '0', '400223', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002224;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002224', '0', '400224', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002225;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002225', '0', '400225', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002226;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002226', '0', '400226', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002227;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002227', '0', '400227', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002228;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002228', '0', '400228', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002229;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002229', '0', '400229', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002230;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002230', '0', '400230', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002231;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002231', '0', '400231', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002232;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002232', '0', '400232', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002233;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002233', '0', '400233', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002234;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002234', '0', '400234', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002235;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002235', '0', '400235', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002236;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002236', '0', '400236', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002237;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002237', '0', '400237', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002238;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002238', '0', '400238', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002239;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002239', '0', '400239', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002240;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002240', '0', '400240', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002241;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002241', '0', '400241', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002242;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002242', '0', '400242', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002243;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002243', '0', '400243', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002244;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002244', '0', '400244', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002245;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002245', '0', '400245', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002246;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002246', '0', '400246', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002247;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002247', '0', '400247', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002248;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002248', '0', '400248', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002249;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002249', '0', '400249', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002250;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002250', '0', '400250', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002251;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002251', '0', '400251', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002252;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002252', '0', '400252', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002253;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002253', '0', '400253', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002254;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002254', '0', '400254', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002255;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002255', '0', '400255', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002256;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002256', '0', '400256', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002258;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002258', '0', '400258', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002259;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002259', '0', '400259', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002260;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002260', '0', '400260', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002261;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002261', '0', '400261', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002262;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002262', '0', '400262', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002264;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002264', '0', '400264', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002265;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002265', '0', '400265', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002266;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002266', '0', '400266', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002267;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002267', '0', '400267', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002268;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002268', '0', '400268', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002269;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002269', '0', '400269', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002270;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002270', '0', '400270', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002271;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002271', '0', '400271', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002272;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002272', '0', '400272', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002273;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002273', '0', '400273', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002274;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002274', '0', '400274', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002275;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002275', '0', '400275', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002276;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002276', '0', '400276', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002277;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002277', '0', '400277', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002278;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002278', '0', '400278', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002280;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002280', '0', '400280', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002281;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002281', '0', '400281', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002282;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002282', '0', '400282', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002284;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002284', '0', '400284', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002286;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002286', '0', '400286', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002288;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002288', '0', '400288', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002289;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002289', '0', '400289', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002292;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002292', '0', '400292', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002294;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002294', '0', '400294', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002295;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002295', '0', '400295', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002296;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002296', '0', '400296', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002297;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002297', '0', '400297', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002298;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002298', '0', '400298', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002299;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002299', '0', '400299', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002300;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002300', '0', '400300', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002301;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002301', '0', '400301', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002302;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002302', '0', '400302', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002303;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002303', '0', '400303', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002304;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002304', '0', '400304', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002305;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002305', '0', '400305', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002306;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002306', '0', '400306', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002307;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002307', '0', '400307', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002308;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002308', '0', '400308', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002309;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002309', '0', '400309', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002311;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002311', '0', '400311', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002313;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002313', '0', '400313', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002315;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002315', '0', '400315', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002316;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002316', '0', '400316', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002317;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002317', '0', '400317', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002318;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002318', '0', '400318', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002320;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002320', '0', '400320', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002321;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002321', '0', '400321', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002322;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002322', '0', '400322', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002323;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002323', '0', '400323', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002325;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002325', '0', '400325', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002326;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002326', '0', '400326', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002327;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002327', '0', '400327', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002328;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002328', '0', '400328', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002329;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002329', '0', '400329', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002330;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002330', '0', '400330', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002331;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002331', '0', '400331', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002332;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002332', '0', '400332', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002333;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002333', '0', '400333', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002334;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002334', '0', '400334', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002335;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002335', '0', '400335', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002336;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002336', '0', '400336', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002337;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002337', '0', '400337', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002338;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002338', '0', '400338', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002339;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002339', '0', '400339', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002340;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002340', '0', '400340', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002341;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002341', '0', '400341', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002342;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002342', '0', '400342', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002343;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002343', '0', '400343', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002344;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002344', '0', '400344', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002345;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002345', '0', '400345', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002346;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002346', '0', '400346', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002347;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002347', '0', '400347', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002348;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002348', '0', '400348', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002349;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002349', '0', '400349', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002350;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002350', '0', '400350', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002351;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002351', '0', '400351', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002352;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002352', '0', '400352', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002353;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002353', '0', '400353', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002354;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002354', '0', '400354', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002356;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002356', '0', '400356', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002357;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002357', '0', '400357', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002358;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002358', '0', '400358', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002359;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002359', '0', '400359', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002360;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002360', '0', '400360', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002361;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002361', '0', '400361', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002362;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002362', '0', '400362', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002363;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002363', '0', '400363', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002364;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002364', '0', '400364', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002365;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002365', '0', '400365', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002366;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002366', '0', '400366', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002367;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002367', '0', '400367', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002369;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002369', '0', '400369', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002370;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002370', '0', '400370', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002371;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002371', '0', '400371', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002372;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002372', '0', '400372', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002373;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002373', '0', '400373', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002374;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002374', '0', '400374', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002375;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002375', '0', '400375', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002376;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002376', '0', '400376', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002377;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002377', '0', '400377', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002378;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002378', '0', '400378', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002379;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002379', '0', '400379', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002380;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002380', '0', '400380', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002381;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002381', '0', '400381', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002382;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002382', '0', '400382', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002383;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002383', '0', '400383', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002384;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002384', '0', '400384', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002385;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002385', '0', '400385', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002386;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002386', '0', '400386', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002387;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002387', '0', '400387', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002388;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002388', '0', '400388', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002389;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002389', '0', '400389', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002390;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002390', '0', '400390', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002391;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002391', '0', '400391', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002392;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002392', '0', '400392', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002393;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002393', '0', '400393', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002394;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002394', '0', '400394', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002395;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002395', '0', '400395', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002396;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002396', '0', '400396', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002397;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002397', '0', '400397', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002398;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002398', '0', '400398', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002399;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002399', '0', '400399', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002400;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002400', '0', '400400', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002402;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002402', '0', '400402', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002403;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002403', '0', '400403', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002404;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002404', '0', '400404', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002405;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002405', '0', '400405', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002406;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002406', '0', '400406', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002408;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002408', '0', '400408', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002409;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002409', '0', '400409', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002410;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002410', '0', '400410', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002411;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002411', '0', '400411', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002412;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002412', '0', '400412', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002413;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002413', '0', '400413', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002414;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002414', '0', '400414', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002415;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002415', '0', '400415', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002416;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002416', '0', '400416', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002418;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002418', '0', '400418', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002420;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002420', '0', '400420', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002421;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002421', '0', '400421', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002422;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002422', '0', '400422', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002423;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002423', '0', '400423', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002424;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002424', '0', '400424', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002425;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002425', '0', '400425', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002426;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002426', '0', '400426', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002427;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002427', '0', '400427', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002428;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002428', '0', '400428', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002429;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002429', '0', '400429', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002430;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002430', '0', '400430', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002431;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002431', '0', '400431', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002432;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002432', '0', '400432', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002434;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002434', '0', '400434', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002435;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002435', '0', '400435', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002436;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002436', '0', '400436', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002438;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002438', '0', '400438', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002440;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002440', '0', '400440', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002442;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002442', '0', '400442', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002444;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002444', '0', '400444', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002445;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002445', '0', '400445', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002446;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002446', '0', '400446', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002447;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002447', '0', '400447', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002448;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002448', '0', '400448', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002449;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002449', '0', '400449', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002450;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002450', '0', '400450', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002451;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002451', '0', '400451', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002452;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002452', '0', '400452', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002453;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002453', '0', '400453', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002456;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002456', '0', '400456', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002457;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002457', '0', '400457', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002458;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002458', '0', '400458', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002459;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002459', '0', '400459', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002460;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002460', '0', '400460', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002461;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002461', '0', '400461', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002462;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002462', '0', '400462', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002463;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002463', '0', '400463', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002464;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002464', '0', '400464', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002465;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002465', '0', '400465', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002466;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002466', '0', '400466', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002467;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002467', '0', '400467', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002468;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002468', '0', '400468', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002469;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002469', '0', '400469', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002470;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002470', '0', '400470', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002471;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002471', '0', '400471', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002472;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002472', '0', '400472', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002473;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002473', '0', '400473', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002474;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002474', '0', '400474', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002475;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002475', '0', '400475', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002477;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002477', '0', '400477', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002479;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002479', '0', '400479', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002480;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002480', '0', '400480', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002481;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002481', '0', '400481', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002483;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002483', '0', '400483', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002484;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002484', '0', '400484', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002485;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002485', '0', '400485', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002486;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002486', '0', '400486', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002487;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002487', '0', '400487', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002489;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002489', '0', '400489', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002491;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002491', '0', '400491', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002493;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002493', '0', '400493', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002495;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002495', '0', '400495', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002496;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002496', '0', '400496', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002497;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002497', '0', '400497', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002498;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002498', '0', '400498', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002499;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002499', '0', '400499', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002500;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002500', '0', '400500', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002501;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002501', '0', '400501', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002502;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002502', '0', '400502', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002503;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002503', '0', '400503', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002504;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002504', '0', '400504', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002505;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002505', '0', '400505', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002506;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002506', '0', '400506', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002507;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002507', '0', '400507', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002508;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002508', '0', '400508', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002509;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002509', '0', '400509', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002510;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002510', '0', '400510', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002511;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002511', '0', '400511', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002512;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002512', '0', '400512', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002513;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002513', '0', '400513', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002514;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002514', '0', '400514', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002515;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002515', '0', '400515', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002516;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002516', '0', '400516', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002517;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002517', '0', '400517', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002518;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002518', '0', '400518', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002519;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002519', '0', '400519', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002520;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002520', '0', '400520', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002521;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002521', '0', '400521', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002522;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002522', '0', '400522', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002523;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002523', '0', '400523', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002524;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002524', '0', '400524', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002525;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002525', '0', '400525', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002526;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002526', '0', '400526', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002527;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002527', '0', '400527', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002529;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002529', '0', '400529', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002530;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002530', '0', '400530', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002534;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002534', '0', '400534', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002535;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002535', '0', '400535', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002536;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002536', '0', '400536', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002537;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002537', '0', '400537', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002538;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002538', '0', '400538', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002539;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002539', '0', '400539', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002540;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002540', '0', '400540', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002541;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002541', '0', '400541', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002542;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002542', '0', '400542', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002543;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002543', '0', '400543', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002544;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002544', '0', '400544', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002545;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002545', '0', '400545', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002546;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002546', '0', '400546', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002547;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002547', '0', '400547', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002548;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002548', '0', '400548', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002549;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002549', '0', '400549', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002550;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002550', '0', '400550', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002551;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002551', '0', '400551', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002554;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002554', '0', '400554', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002555;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002555', '0', '400555', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002556;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002556', '0', '400556', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002557;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002557', '0', '400557', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002558;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002558', '0', '400558', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002559;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002559', '0', '400559', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002560;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002560', '0', '400560', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002561;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002561', '0', '400561', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002563;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002563', '0', '400563', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002569;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002569', '0', '400569', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002570;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002570', '0', '400570', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002572;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002572', '0', '400572', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002573;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002573', '0', '400573', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002574;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002574', '0', '400574', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002575;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002575', '0', '400575', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002576;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002576', '0', '400576', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002577;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002577', '0', '400577', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002578;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002578', '0', '400578', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002579;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002579', '0', '400579', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002580;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002580', '0', '400580', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002581;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002581', '0', '400581', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002582;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002582', '0', '400582', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002583;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002583', '0', '400583', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002584;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002584', '0', '400584', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002585;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002585', '0', '400585', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002586;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002586', '0', '400586', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002587;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002587', '0', '400587', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002588;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002588', '0', '400588', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002589;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002589', '0', '400589', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002590;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002590', '0', '400590', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002591;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002591', '0', '400591', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002592;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002592', '0', '400592', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002593;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002593', '0', '400593', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002594;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002594', '0', '400594', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002595;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002595', '0', '400595', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002596;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002596', '0', '400596', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002601;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002601', '0', '400601', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002602;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002602', '0', '400602', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002603;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002603', '0', '400603', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002604;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002604', '0', '400604', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002606;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002606', '0', '400606', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002608;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002608', '0', '400608', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002610;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002610', '0', '400610', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002611;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002611', '0', '400611', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002614;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002614', '0', '400614', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002615;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002615', '0', '400615', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002616;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002616', '0', '400616', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002617;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002617', '0', '400617', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002618;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002618', '0', '400618', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002619;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002619', '0', '400619', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002620;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002620', '0', '400620', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002621;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002621', '0', '400621', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002622;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002622', '0', '400622', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002623;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002623', '0', '400623', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002624;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002624', '0', '400624', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002625;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002625', '0', '400625', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002626;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002626', '0', '400626', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002627;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002627', '0', '400627', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002628;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002628', '0', '400628', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002629;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002629', '0', '400629', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002630;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002630', '0', '400630', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002631;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002631', '0', '400631', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002632;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002632', '0', '400632', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002633;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002633', '0', '400633', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002634;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002634', '0', '400634', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002635;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002635', '0', '400635', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002636;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002636', '0', '400636', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002637;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002637', '0', '400637', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002638;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002638', '0', '400638', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002641;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002641', '0', '400641', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002642;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002642', '0', '400642', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002643;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002643', '0', '400643', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002644;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002644', '0', '400644', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002645;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002645', '0', '400645', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002646;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002646', '0', '400646', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002647;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002647', '0', '400647', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002649;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002649', '0', '400649', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002650;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002650', '0', '400650', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002652;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002652', '0', '400652', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002654;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002654', '0', '400654', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002655;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002655', '0', '400655', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002656;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002656', '0', '400656', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002658;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002658', '0', '400658', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002660;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002660', '0', '400660', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002662;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002662', '0', '400662', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002664;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002664', '0', '400664', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002666;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002666', '0', '400666', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002668;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002668', '0', '400668', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002670;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002670', '0', '400670', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002671;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002671', '0', '400671', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002672;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002672', '0', '400672', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002673;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002673', '0', '400673', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002674;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002674', '0', '400674', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002675;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002675', '0', '400675', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002676;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002676', '0', '400676', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002677;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002677', '0', '400677', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002678;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002678', '0', '400678', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002679;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002679', '0', '400679', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002680;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002680', '0', '400680', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002681;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002681', '0', '400681', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002682;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002682', '0', '400682', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002683;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002683', '0', '400683', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002684;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002684', '0', '400684', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002685;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002685', '0', '400685', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002686;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002686', '0', '400686', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002687;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002687', '0', '400687', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002688;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002688', '0', '400688', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002689;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002689', '0', '400689', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002690;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002690', '0', '400690', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002691;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002691', '0', '400691', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002692;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002692', '0', '400692', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002693;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002693', '0', '400693', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002694;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002694', '0', '400694', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002695;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002695', '0', '400695', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002696;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002696', '0', '400696', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002697;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002697', '0', '400697', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002698;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002698', '0', '400698', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002699;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002699', '0', '400699', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002701;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002701', '0', '400701', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002702;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002702', '0', '400702', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002703;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002703', '0', '400703', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002704;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002704', '0', '400704', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002705;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002705', '0', '400705', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002706;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002706', '0', '400706', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002707;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002707', '0', '400707', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002708;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002708', '0', '400708', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002709;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002709', '0', '400709', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002710;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002710', '0', '400710', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002711;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002711', '0', '400711', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002712;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002712', '0', '400712', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002713;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002713', '0', '400713', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002714;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002714', '0', '400714', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002715;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002715', '0', '400715', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002716;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002716', '0', '400716', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002717;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002717', '0', '400717', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002718;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002718', '0', '400718', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002719;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002719', '0', '400719', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002720;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002720', '0', '400720', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002721;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002721', '0', '400721', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002722;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002722', '0', '400722', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002723;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002723', '0', '400723', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002724;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002724', '0', '400724', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002725;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002725', '0', '400725', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002726;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002726', '0', '400726', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002727;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002727', '0', '400727', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002728;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002728', '0', '400728', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002729;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002729', '0', '400729', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002730;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002730', '0', '400730', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002731;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002731', '0', '400731', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002733;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002733', '0', '400733', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002734;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002734', '0', '400734', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002736;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002736', '0', '400736', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002737;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002737', '0', '400737', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002738;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002738', '0', '400738', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002740;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002740', '0', '400740', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002742;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002742', '0', '400742', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002744;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002744', '0', '400744', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002746;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002746', '0', '400746', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002748;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002748', '0', '400748', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002750;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002750', '0', '400750', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002751;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002751', '0', '400751', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002752;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002752', '0', '400752', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002754;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002754', '0', '400754', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002755;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002755', '0', '400755', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002756;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002756', '0', '400756', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002757;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002757', '0', '400757', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002758;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002758', '0', '400758', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002759;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002759', '0', '400759', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002760;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002760', '0', '400760', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002761;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002761', '0', '400761', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002762;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002762', '0', '400762', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002763;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002763', '0', '400763', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002764;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002764', '0', '400764', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002765;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002765', '0', '400765', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002766;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002766', '0', '400766', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002767;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002767', '0', '400767', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002768;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002768', '0', '400768', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002769;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002769', '0', '400769', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002770;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002770', '0', '400770', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002771;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002771', '0', '400771', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002773;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002773', '0', '400773', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002774;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002774', '0', '400774', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002776;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002776', '0', '400776', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002778;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002778', '0', '400778', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002780;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002780', '0', '400780', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002781;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002781', '0', '400781', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002782;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002782', '0', '400782', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002783;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002783', '0', '400783', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002784;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002784', '0', '400784', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002785;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002785', '0', '400785', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002786;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002786', '0', '400786', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002787;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002787', '0', '400787', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002788;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002788', '0', '400788', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002789;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002789', '0', '400789', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002790;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002790', '0', '400790', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002791;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002791', '0', '400791', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002792;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002792', '0', '400792', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002793;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002793', '0', '400793', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002794;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002794', '0', '400794', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002795;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002795', '0', '400795', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002796;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002796', '0', '400796', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002797;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002797', '0', '400797', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002798;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002798', '0', '400798', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002799;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002799', '0', '400799', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002800;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002800', '0', '400800', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002801;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002801', '0', '400801', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002802;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002802', '0', '400802', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002803;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002803', '0', '400803', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002804;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002804', '0', '400804', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002805;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002805', '0', '400805', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002806;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002806', '0', '400806', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002807;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002807', '0', '400807', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002808;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002808', '0', '400808', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002809;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002809', '0', '400809', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002810;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002810', '0', '400810', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002811;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002811', '0', '400811', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002812;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002812', '0', '400812', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002813;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002813', '0', '400813', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002814;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002814', '0', '400814', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002815;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002815', '0', '400815', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002816;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002816', '0', '400816', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002817;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002817', '0', '400817', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002818;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002818', '0', '400818', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002819;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002819', '0', '400819', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002820;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002820', '0', '400820', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002821;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002821', '0', '400821', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002822;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002822', '0', '400822', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002823;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002823', '0', '400823', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002824;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002824', '0', '400824', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002825;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002825', '0', '400825', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002826;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002826', '0', '400826', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002827;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002827', '0', '400827', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002828;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002828', '0', '400828', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002829;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002829', '0', '400829', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002830;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002830', '0', '400830', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002831;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002831', '0', '400831', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002832;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002832', '0', '400832', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002833;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002833', '0', '400833', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002834;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002834', '0', '400834', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002836;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002836', '0', '400836', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002837;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002837', '0', '400837', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002838;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002838', '0', '400838', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002839;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002839', '0', '400839', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002840;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002840', '0', '400840', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002841;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002841', '0', '400841', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002842;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002842', '0', '400842', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002843;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002843', '0', '400843', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002844;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002844', '0', '400844', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002845;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002845', '0', '400845', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002846;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002846', '0', '400846', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002847;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002847', '0', '400847', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002848;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002848', '0', '400848', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002849;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002849', '0', '400849', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002850;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002850', '0', '400850', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002851;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002851', '0', '400851', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002852;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002852', '0', '400852', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002853;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002853', '0', '400853', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002854;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002854', '0', '400854', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002855;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002855', '0', '400855', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002856;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002856', '0', '400856', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002858;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002858', '0', '400858', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002860;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002860', '0', '400860', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002861;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002861', '0', '400861', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002862;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002862', '0', '400862', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002863;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002863', '0', '400863', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002865;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002865', '0', '400865', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002866;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002866', '0', '400866', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002867;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002867', '0', '400867', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002869;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002869', '0', '400869', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002871;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002871', '0', '400871', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002872;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002872', '0', '400872', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002874;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002874', '0', '400874', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002876;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002876', '0', '400876', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002877;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002877', '0', '400877', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002878;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002878', '0', '400878', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002879;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002879', '0', '400879', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002880;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002880', '0', '400880', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002881;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002881', '0', '400881', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002882;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002882', '0', '400882', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002883;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002883', '0', '400883', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002884;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002884', '0', '400884', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002885;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002885', '0', '400885', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002886;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002886', '0', '400886', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002887;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002887', '0', '400887', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002888;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002888', '0', '400888', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002889;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002889', '0', '400889', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002890;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002890', '0', '400890', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002891;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002891', '0', '400891', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002892;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002892', '0', '400892', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002893;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002893', '0', '400893', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002894;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002894', '0', '400894', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002896;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002896', '0', '400896', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002898;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002898', '0', '400898', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002900;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002900', '0', '400900', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002902;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002902', '0', '400902', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002904;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002904', '0', '400904', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002905;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002905', '0', '400905', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002906;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002906', '0', '400906', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002907;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002907', '0', '400907', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002908;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002908', '0', '400908', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002909;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002909', '0', '400909', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002911;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002911', '0', '400911', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002913;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002913', '0', '400913', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002915;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002915', '0', '400915', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002916;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002916', '0', '400916', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002917;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002917', '0', '400917', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002918;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002918', '0', '400918', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002919;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002919', '0', '400919', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002921;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002921', '0', '400921', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002922;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002922', '0', '400922', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002923;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002923', '0', '400923', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002925;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002925', '0', '400925', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002927;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002927', '0', '400927', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002929;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002929', '0', '400929', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002931;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002931', '0', '400931', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002932;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002932', '0', '400932', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002933;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002933', '0', '400933', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002934;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002934', '0', '400934', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002936;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002936', '0', '400936', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002937;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002937', '0', '400937', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002938;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002938', '0', '400938', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002941;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002941', '0', '400941', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002942;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002942', '0', '400942', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002943;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002943', '0', '400943', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002944;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002944', '0', '400944', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002946;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002946', '0', '400946', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002947;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002947', '0', '400947', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002948;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002948', '0', '400948', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002950;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002950', '0', '400950', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002952;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002952', '0', '400952', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002954;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002954', '0', '400954', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002956;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002956', '0', '400956', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002958;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002958', '0', '400958', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002960;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002960', '0', '400960', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002961;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002961', '0', '400961', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002963;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002963', '0', '400963', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002964;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002964', '0', '400964', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002966;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002966', '0', '400966', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002968;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002968', '0', '400968', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002970;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002970', '0', '400970', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002971;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002971', '0', '400971', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002974;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002974', '0', '400974', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002976;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002976', '0', '400976', '1', '1', '12340');

DELETE FROM `creature_template_model` WHERE `CreatureID`=1002978;
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
('1002978', '0', '400978', '1', '1', '12340');

DELETE FROM `creature_model_info` WHERE `DisplayID` BETWEEN 400000 AND 400979;
INSERT INTO `creature_model_info` (`DisplayID`, `BoundingRadius`, `CombatReach`, `Gender`, `DisplayID_Other_Gender`, `VerifiedBuild`) VALUES
('400000', '0.5', '1', '2', '0', '12340'),
('400001', '0.5', '1', '2', '0', '12340'),
('400002', '0.5', '1', '2', '0', '12340'),
('400003', '0.5', '1', '2', '0', '12340'),
('400004', '0.5', '1', '2', '0', '12340'),
('400005', '0.5', '1', '2', '0', '12340'),
('400006', '0.5', '1', '2', '0', '12340'),
('400007', '0.5', '1', '2', '0', '12340'),
('400008', '0.5', '1', '2', '0', '12340'),
('400009', '0.5', '1', '2', '0', '12340'),
('400010', '0.5', '1', '2', '0', '12340'),
('400011', '0.5', '1', '2', '0', '12340'),
('400012', '0.5', '1', '2', '0', '12340'),
('400013', '0.5', '1', '2', '0', '12340'),
('400014', '0.5', '1', '2', '0', '12340'),
('400015', '0.5', '1', '2', '0', '12340'),
('400016', '0.5', '1', '2', '0', '12340'),
('400017', '0.5', '1', '2', '0', '12340'),
('400018', '0.5', '1', '2', '0', '12340'),
('400019', '0.5', '1', '2', '0', '12340'),
('400020', '0.5', '1', '2', '0', '12340'),
('400021', '0.5', '1', '2', '0', '12340'),
('400022', '0.5', '1', '2', '0', '12340'),
('400023', '0.5', '1', '2', '0', '12340'),
('400024', '0.5', '1', '2', '0', '12340'),
('400025', '0.5', '1', '2', '0', '12340'),
('400026', '0.5', '1', '2', '0', '12340'),
('400027', '0.5', '1', '2', '0', '12340'),
('400028', '0.5', '1', '2', '0', '12340'),
('400029', '0.5', '1', '2', '0', '12340'),
('400030', '0.5', '1', '2', '0', '12340'),
('400031', '0.5', '1', '2', '0', '12340'),
('400032', '0.5', '1', '2', '0', '12340'),
('400033', '0.5', '1', '2', '0', '12340'),
('400034', '0.5', '1', '2', '0', '12340'),
('400035', '0.5', '1', '2', '0', '12340'),
('400036', '0.5', '1', '2', '0', '12340'),
('400037', '0.5', '1', '2', '0', '12340'),
('400038', '0.5', '1', '2', '0', '12340'),
('400039', '0.5', '1', '2', '0', '12340'),
('400040', '0.5', '1', '2', '0', '12340'),
('400041', '0.5', '1', '2', '0', '12340'),
('400042', '0.5', '1', '2', '0', '12340'),
('400043', '0.5', '1', '2', '0', '12340'),
('400044', '0.5', '1', '2', '0', '12340'),
('400045', '0.5', '1', '2', '0', '12340'),
('400046', '0.5', '1', '2', '0', '12340'),
('400047', '0.5', '1', '2', '0', '12340'),
('400048', '0.5', '1', '2', '0', '12340'),
('400049', '0.5', '1', '2', '0', '12340'),
('400050', '0.5', '1', '2', '0', '12340'),
('400051', '0.5', '1', '2', '0', '12340'),
('400052', '0.5', '1', '2', '0', '12340'),
('400053', '0.5', '1', '2', '0', '12340'),
('400054', '0.5', '1', '2', '0', '12340'),
('400055', '0.5', '1', '2', '0', '12340'),
('400056', '0.5', '1', '2', '0', '12340'),
('400057', '0.5', '1', '2', '0', '12340'),
('400058', '0.5', '1', '2', '0', '12340'),
('400059', '0.5', '1', '2', '0', '12340'),
('400060', '0.5', '1', '2', '0', '12340'),
('400061', '0.5', '1', '2', '0', '12340'),
('400062', '0.5', '1', '2', '0', '12340'),
('400063', '0.5', '1', '2', '0', '12340'),
('400064', '0.5', '1', '2', '0', '12340'),
('400065', '0.5', '1', '2', '0', '12340'),
('400066', '0.5', '1', '2', '0', '12340'),
('400067', '0.5', '1', '2', '0', '12340'),
('400068', '0.5', '1', '2', '0', '12340'),
('400069', '0.5', '1', '2', '0', '12340'),
('400070', '0.5', '1', '2', '0', '12340'),
('400071', '0.5', '1', '2', '0', '12340'),
('400072', '0.5', '1', '2', '0', '12340'),
('400073', '0.5', '1', '2', '0', '12340'),
('400074', '0.5', '1', '2', '0', '12340'),
('400075', '0.5', '1', '2', '0', '12340'),
('400076', '0.5', '1', '2', '0', '12340'),
('400077', '0.5', '1', '2', '0', '12340'),
('400078', '0.5', '1', '2', '0', '12340'),
('400079', '0.5', '1', '2', '0', '12340'),
('400080', '0.5', '1', '2', '0', '12340'),
('400081', '0.5', '1', '2', '0', '12340'),
('400082', '0.5', '1', '2', '0', '12340'),
('400083', '0.5', '1', '2', '0', '12340'),
('400084', '0.5', '1', '2', '0', '12340'),
('400085', '0.5', '1', '2', '0', '12340'),
('400086', '0.5', '1', '2', '0', '12340'),
('400087', '0.5', '1', '2', '0', '12340'),
('400088', '0.5', '1', '2', '0', '12340'),
('400089', '0.5', '1', '2', '0', '12340'),
('400090', '0.5', '1', '2', '0', '12340'),
('400091', '0.5', '1', '2', '0', '12340'),
('400092', '0.5', '1', '2', '0', '12340'),
('400093', '0.5', '1', '2', '0', '12340'),
('400094', '0.5', '1', '2', '0', '12340'),
('400095', '0.5', '1', '2', '0', '12340'),
('400096', '0.5', '1', '2', '0', '12340'),
('400097', '0.5', '1', '2', '0', '12340'),
('400098', '0.5', '1', '2', '0', '12340'),
('400099', '0.5', '1', '2', '0', '12340'),
('400100', '0.5', '1', '2', '0', '12340'),
('400101', '0.5', '1', '2', '0', '12340'),
('400102', '0.5', '1', '2', '0', '12340'),
('400103', '0.5', '1', '2', '0', '12340'),
('400104', '0.5', '1', '2', '0', '12340'),
('400105', '0.5', '1', '2', '0', '12340'),
('400106', '0.5', '1', '2', '0', '12340'),
('400107', '0.5', '1', '2', '0', '12340'),
('400108', '0.5', '1', '2', '0', '12340'),
('400109', '0.5', '1', '2', '0', '12340'),
('400110', '0.5', '1', '2', '0', '12340'),
('400111', '0.5', '1', '2', '0', '12340'),
('400112', '0.5', '1', '2', '0', '12340'),
('400113', '0.5', '1', '2', '0', '12340'),
('400114', '0.5', '1', '2', '0', '12340'),
('400115', '0.5', '1', '2', '0', '12340'),
('400116', '0.5', '1', '2', '0', '12340'),
('400117', '0.5', '1', '2', '0', '12340'),
('400118', '0.5', '1', '2', '0', '12340'),
('400119', '0.5', '1', '2', '0', '12340'),
('400120', '0.5', '1', '2', '0', '12340'),
('400121', '0.5', '1', '2', '0', '12340'),
('400122', '0.5', '1', '2', '0', '12340'),
('400123', '0.5', '1', '2', '0', '12340'),
('400124', '0.5', '1', '2', '0', '12340'),
('400125', '0.5', '1', '2', '0', '12340'),
('400126', '0.5', '1', '2', '0', '12340'),
('400127', '0.5', '1', '2', '0', '12340'),
('400128', '0.5', '1', '2', '0', '12340'),
('400129', '0.5', '1', '2', '0', '12340'),
('400130', '0.5', '1', '2', '0', '12340'),
('400131', '0.5', '1', '2', '0', '12340'),
('400132', '0.5', '1', '2', '0', '12340'),
('400133', '0.5', '1', '2', '0', '12340'),
('400134', '0.5', '1', '2', '0', '12340'),
('400135', '0.5', '1', '2', '0', '12340'),
('400136', '0.5', '1', '2', '0', '12340'),
('400137', '0.5', '1', '2', '0', '12340'),
('400138', '0.5', '1', '2', '0', '12340'),
('400139', '0.5', '1', '2', '0', '12340'),
('400140', '0.5', '1', '2', '0', '12340'),
('400141', '0.5', '1', '2', '0', '12340'),
('400142', '0.5', '1', '2', '0', '12340'),
('400143', '0.5', '1', '2', '0', '12340'),
('400144', '0.5', '1', '2', '0', '12340'),
('400145', '0.5', '1', '2', '0', '12340'),
('400146', '0.5', '1', '2', '0', '12340'),
('400147', '0.5', '1', '2', '0', '12340'),
('400148', '0.5', '1', '2', '0', '12340'),
('400149', '0.5', '1', '2', '0', '12340'),
('400150', '0.5', '1', '2', '0', '12340'),
('400151', '0.5', '1', '2', '0', '12340'),
('400152', '0.5', '1', '2', '0', '12340'),
('400153', '0.5', '1', '2', '0', '12340'),
('400154', '0.5', '1', '2', '0', '12340'),
('400155', '0.5', '1', '2', '0', '12340'),
('400156', '0.5', '1', '2', '0', '12340'),
('400157', '0.5', '1', '2', '0', '12340'),
('400158', '0.5', '1', '2', '0', '12340'),
('400159', '0.5', '1', '2', '0', '12340'),
('400160', '0.5', '1', '2', '0', '12340'),
('400161', '0.5', '1', '2', '0', '12340'),
('400162', '0.5', '1', '2', '0', '12340'),
('400163', '0.5', '1', '2', '0', '12340'),
('400164', '0.5', '1', '2', '0', '12340'),
('400165', '0.5', '1', '2', '0', '12340'),
('400166', '0.5', '1', '2', '0', '12340'),
('400167', '0.5', '1', '2', '0', '12340'),
('400168', '0.5', '1', '2', '0', '12340'),
('400169', '0.5', '1', '2', '0', '12340'),
('400170', '0.5', '1', '2', '0', '12340'),
('400171', '0.5', '1', '2', '0', '12340'),
('400172', '0.5', '1', '2', '0', '12340'),
('400173', '0.5', '1', '2', '0', '12340'),
('400174', '0.5', '1', '2', '0', '12340'),
('400175', '0.5', '1', '2', '0', '12340'),
('400176', '0.5', '1', '2', '0', '12340'),
('400177', '0.5', '1', '2', '0', '12340'),
('400178', '0.5', '1', '2', '0', '12340'),
('400179', '0.5', '1', '2', '0', '12340'),
('400180', '0.5', '1', '2', '0', '12340'),
('400181', '0.5', '1', '2', '0', '12340'),
('400182', '0.5', '1', '2', '0', '12340'),
('400183', '0.5', '1', '2', '0', '12340'),
('400184', '0.5', '1', '2', '0', '12340'),
('400185', '0.5', '1', '2', '0', '12340'),
('400186', '0.5', '1', '2', '0', '12340'),
('400187', '0.5', '1', '2', '0', '12340'),
('400188', '0.5', '1', '2', '0', '12340'),
('400189', '0.5', '1', '2', '0', '12340'),
('400190', '0.5', '1', '2', '0', '12340'),
('400191', '0.5', '1', '2', '0', '12340'),
('400192', '0.5', '1', '2', '0', '12340'),
('400193', '0.5', '1', '2', '0', '12340'),
('400194', '0.5', '1', '2', '0', '12340'),
('400195', '0.5', '1', '2', '0', '12340'),
('400196', '0.5', '1', '2', '0', '12340'),
('400197', '0.5', '1', '2', '0', '12340'),
('400198', '0.5', '1', '2', '0', '12340'),
('400199', '0.5', '1', '2', '0', '12340'),
('400200', '0.5', '1', '2', '0', '12340'),
('400201', '0.5', '1', '2', '0', '12340'),
('400202', '0.5', '1', '2', '0', '12340'),
('400203', '0.5', '1', '2', '0', '12340'),
('400204', '0.5', '1', '2', '0', '12340'),
('400205', '0.5', '1', '2', '0', '12340'),
('400206', '0.5', '1', '2', '0', '12340'),
('400207', '0.5', '1', '2', '0', '12340'),
('400208', '0.5', '1', '2', '0', '12340'),
('400209', '0.5', '1', '2', '0', '12340'),
('400210', '0.5', '1', '2', '0', '12340'),
('400211', '0.5', '1', '2', '0', '12340'),
('400212', '0.5', '1', '2', '0', '12340'),
('400213', '0.5', '1', '2', '0', '12340'),
('400214', '0.5', '1', '2', '0', '12340'),
('400215', '0.5', '1', '2', '0', '12340'),
('400216', '0.5', '1', '2', '0', '12340'),
('400217', '0.5', '1', '2', '0', '12340'),
('400218', '0.5', '1', '2', '0', '12340'),
('400219', '0.5', '1', '2', '0', '12340'),
('400220', '0.5', '1', '2', '0', '12340'),
('400221', '0.5', '1', '2', '0', '12340'),
('400222', '0.5', '1', '2', '0', '12340'),
('400223', '0.5', '1', '2', '0', '12340'),
('400224', '0.5', '1', '2', '0', '12340'),
('400225', '0.5', '1', '2', '0', '12340'),
('400226', '0.5', '1', '2', '0', '12340'),
('400227', '0.5', '1', '2', '0', '12340'),
('400228', '0.5', '1', '2', '0', '12340'),
('400229', '0.5', '1', '2', '0', '12340'),
('400230', '0.5', '1', '2', '0', '12340'),
('400231', '0.5', '1', '2', '0', '12340'),
('400232', '0.5', '1', '2', '0', '12340'),
('400233', '0.5', '1', '2', '0', '12340'),
('400234', '0.5', '1', '2', '0', '12340'),
('400235', '0.5', '1', '2', '0', '12340'),
('400236', '0.5', '1', '2', '0', '12340'),
('400237', '0.5', '1', '2', '0', '12340'),
('400238', '0.5', '1', '2', '0', '12340'),
('400239', '0.5', '1', '2', '0', '12340'),
('400240', '0.5', '1', '2', '0', '12340'),
('400241', '0.5', '1', '2', '0', '12340'),
('400242', '0.5', '1', '2', '0', '12340'),
('400243', '0.5', '1', '2', '0', '12340'),
('400244', '0.5', '1', '2', '0', '12340'),
('400245', '0.5', '1', '2', '0', '12340'),
('400246', '0.5', '1', '2', '0', '12340'),
('400247', '0.5', '1', '2', '0', '12340'),
('400248', '0.5', '1', '2', '0', '12340'),
('400249', '0.5', '1', '2', '0', '12340'),
('400250', '0.5', '1', '2', '0', '12340'),
('400251', '0.5', '1', '2', '0', '12340'),
('400252', '0.5', '1', '2', '0', '12340'),
('400253', '0.5', '1', '2', '0', '12340'),
('400254', '0.5', '1', '2', '0', '12340'),
('400255', '0.5', '1', '2', '0', '12340'),
('400256', '0.5', '1', '2', '0', '12340'),
('400257', '0.5', '1', '2', '0', '12340'),
('400258', '0.5', '1', '2', '0', '12340'),
('400259', '0.5', '1', '2', '0', '12340'),
('400260', '0.5', '1', '2', '0', '12340'),
('400261', '0.5', '1', '2', '0', '12340'),
('400262', '0.5', '1', '2', '0', '12340'),
('400263', '0.5', '1', '2', '0', '12340'),
('400264', '0.5', '1', '2', '0', '12340'),
('400265', '0.5', '1', '2', '0', '12340'),
('400266', '0.5', '1', '2', '0', '12340'),
('400267', '0.5', '1', '2', '0', '12340'),
('400268', '0.5', '1', '2', '0', '12340'),
('400269', '0.5', '1', '2', '0', '12340'),
('400270', '0.5', '1', '2', '0', '12340'),
('400271', '0.5', '1', '2', '0', '12340'),
('400272', '0.5', '1', '2', '0', '12340'),
('400273', '0.5', '1', '2', '0', '12340'),
('400274', '0.5', '1', '2', '0', '12340'),
('400275', '0.5', '1', '2', '0', '12340'),
('400276', '0.5', '1', '2', '0', '12340'),
('400277', '0.5', '1', '2', '0', '12340'),
('400278', '0.5', '1', '2', '0', '12340'),
('400279', '0.5', '1', '2', '0', '12340'),
('400280', '0.5', '1', '2', '0', '12340'),
('400281', '0.5', '1', '2', '0', '12340'),
('400282', '0.5', '1', '2', '0', '12340'),
('400283', '0.5', '1', '2', '0', '12340'),
('400284', '0.5', '1', '2', '0', '12340'),
('400285', '0.5', '1', '2', '0', '12340'),
('400286', '0.5', '1', '2', '0', '12340'),
('400287', '0.5', '1', '2', '0', '12340'),
('400288', '0.5', '1', '2', '0', '12340'),
('400289', '0.5', '1', '2', '0', '12340'),
('400290', '0.5', '1', '2', '0', '12340'),
('400291', '0.5', '1', '2', '0', '12340'),
('400292', '0.5', '1', '2', '0', '12340'),
('400293', '0.5', '1', '2', '0', '12340'),
('400294', '0.5', '1', '2', '0', '12340'),
('400295', '0.5', '1', '2', '0', '12340'),
('400296', '0.5', '1', '2', '0', '12340'),
('400297', '0.5', '1', '2', '0', '12340'),
('400298', '0.5', '1', '2', '0', '12340'),
('400299', '0.5', '1', '2', '0', '12340'),
('400300', '0.5', '1', '2', '0', '12340'),
('400301', '0.5', '1', '2', '0', '12340'),
('400302', '0.5', '1', '2', '0', '12340'),
('400303', '0.5', '1', '2', '0', '12340'),
('400304', '0.5', '1', '2', '0', '12340'),
('400305', '0.5', '1', '2', '0', '12340'),
('400306', '0.5', '1', '2', '0', '12340'),
('400307', '0.5', '1', '2', '0', '12340'),
('400308', '0.5', '1', '2', '0', '12340'),
('400309', '0.5', '1', '2', '0', '12340'),
('400310', '0.5', '1', '2', '0', '12340'),
('400311', '0.5', '1', '2', '0', '12340'),
('400312', '0.5', '1', '2', '0', '12340'),
('400313', '0.5', '1', '2', '0', '12340'),
('400314', '0.5', '1', '2', '0', '12340'),
('400315', '0.5', '1', '2', '0', '12340'),
('400316', '0.5', '1', '2', '0', '12340'),
('400317', '0.5', '1', '2', '0', '12340'),
('400318', '0.5', '1', '2', '0', '12340'),
('400319', '0.5', '1', '2', '0', '12340'),
('400320', '0.5', '1', '2', '0', '12340'),
('400321', '0.5', '1', '2', '0', '12340'),
('400322', '0.5', '1', '2', '0', '12340'),
('400323', '0.5', '1', '2', '0', '12340'),
('400324', '0.5', '1', '2', '0', '12340'),
('400325', '0.5', '1', '2', '0', '12340'),
('400326', '0.5', '1', '2', '0', '12340'),
('400327', '0.5', '1', '2', '0', '12340'),
('400328', '0.5', '1', '2', '0', '12340'),
('400329', '0.5', '1', '2', '0', '12340'),
('400330', '0.5', '1', '2', '0', '12340'),
('400331', '0.5', '1', '2', '0', '12340'),
('400332', '0.5', '1', '2', '0', '12340'),
('400333', '0.5', '1', '2', '0', '12340'),
('400334', '0.5', '1', '2', '0', '12340'),
('400335', '0.5', '1', '2', '0', '12340'),
('400336', '0.5', '1', '2', '0', '12340'),
('400337', '0.5', '1', '2', '0', '12340'),
('400338', '0.5', '1', '2', '0', '12340'),
('400339', '0.5', '1', '2', '0', '12340'),
('400340', '0.5', '1', '2', '0', '12340'),
('400341', '0.5', '1', '2', '0', '12340'),
('400342', '0.5', '1', '2', '0', '12340'),
('400343', '0.5', '1', '2', '0', '12340'),
('400344', '0.5', '1', '2', '0', '12340'),
('400345', '0.5', '1', '2', '0', '12340'),
('400346', '0.5', '1', '2', '0', '12340'),
('400347', '0.5', '1', '2', '0', '12340'),
('400348', '0.5', '1', '2', '0', '12340'),
('400349', '0.5', '1', '2', '0', '12340'),
('400350', '0.5', '1', '2', '0', '12340'),
('400351', '0.5', '1', '2', '0', '12340'),
('400352', '0.5', '1', '2', '0', '12340'),
('400353', '0.5', '1', '2', '0', '12340'),
('400354', '0.5', '1', '2', '0', '12340'),
('400355', '0.5', '1', '2', '0', '12340'),
('400356', '0.5', '1', '2', '0', '12340'),
('400357', '0.5', '1', '2', '0', '12340'),
('400358', '0.5', '1', '2', '0', '12340'),
('400359', '0.5', '1', '2', '0', '12340'),
('400360', '0.5', '1', '2', '0', '12340'),
('400361', '0.5', '1', '2', '0', '12340'),
('400362', '0.5', '1', '2', '0', '12340'),
('400363', '0.5', '1', '2', '0', '12340'),
('400364', '0.5', '1', '2', '0', '12340'),
('400365', '0.5', '1', '2', '0', '12340'),
('400366', '0.5', '1', '2', '0', '12340'),
('400367', '0.5', '1', '2', '0', '12340'),
('400368', '0.5', '1', '2', '0', '12340'),
('400369', '0.5', '1', '2', '0', '12340'),
('400370', '0.5', '1', '2', '0', '12340'),
('400371', '0.5', '1', '2', '0', '12340'),
('400372', '0.5', '1', '2', '0', '12340'),
('400373', '0.5', '1', '2', '0', '12340'),
('400374', '0.5', '1', '2', '0', '12340'),
('400375', '0.5', '1', '2', '0', '12340'),
('400376', '0.5', '1', '2', '0', '12340'),
('400377', '0.5', '1', '2', '0', '12340'),
('400378', '0.5', '1', '2', '0', '12340'),
('400379', '0.5', '1', '2', '0', '12340'),
('400380', '0.5', '1', '2', '0', '12340'),
('400381', '0.5', '1', '2', '0', '12340'),
('400382', '0.5', '1', '2', '0', '12340'),
('400383', '0.5', '1', '2', '0', '12340'),
('400384', '0.5', '1', '2', '0', '12340'),
('400385', '0.5', '1', '2', '0', '12340'),
('400386', '0.5', '1', '2', '0', '12340'),
('400387', '0.5', '1', '2', '0', '12340'),
('400388', '0.5', '1', '2', '0', '12340'),
('400389', '0.5', '1', '2', '0', '12340'),
('400390', '0.5', '1', '2', '0', '12340'),
('400391', '0.5', '1', '2', '0', '12340'),
('400392', '0.5', '1', '2', '0', '12340'),
('400393', '0.5', '1', '2', '0', '12340'),
('400394', '0.5', '1', '2', '0', '12340'),
('400395', '0.5', '1', '2', '0', '12340'),
('400396', '0.5', '1', '2', '0', '12340'),
('400397', '0.5', '1', '2', '0', '12340'),
('400398', '0.5', '1', '2', '0', '12340'),
('400399', '0.5', '1', '2', '0', '12340'),
('400400', '0.5', '1', '2', '0', '12340'),
('400401', '0.5', '1', '2', '0', '12340'),
('400402', '0.5', '1', '2', '0', '12340'),
('400403', '0.5', '1', '2', '0', '12340'),
('400404', '0.5', '1', '2', '0', '12340'),
('400405', '0.5', '1', '2', '0', '12340'),
('400406', '0.5', '1', '2', '0', '12340'),
('400407', '0.5', '1', '2', '0', '12340'),
('400408', '0.5', '1', '2', '0', '12340'),
('400409', '0.5', '1', '2', '0', '12340'),
('400410', '0.5', '1', '2', '0', '12340'),
('400411', '0.5', '1', '2', '0', '12340'),
('400412', '0.5', '1', '2', '0', '12340'),
('400413', '0.5', '1', '2', '0', '12340'),
('400414', '0.5', '1', '2', '0', '12340'),
('400415', '0.5', '1', '2', '0', '12340'),
('400416', '0.5', '1', '2', '0', '12340'),
('400417', '0.5', '1', '2', '0', '12340'),
('400418', '0.5', '1', '2', '0', '12340'),
('400419', '0.5', '1', '2', '0', '12340'),
('400420', '0.5', '1', '2', '0', '12340'),
('400421', '0.5', '1', '2', '0', '12340'),
('400422', '0.5', '1', '2', '0', '12340'),
('400423', '0.5', '1', '2', '0', '12340'),
('400424', '0.5', '1', '2', '0', '12340'),
('400425', '0.5', '1', '2', '0', '12340'),
('400426', '0.5', '1', '2', '0', '12340'),
('400427', '0.5', '1', '2', '0', '12340'),
('400428', '0.5', '1', '2', '0', '12340'),
('400429', '0.5', '1', '2', '0', '12340'),
('400430', '0.5', '1', '2', '0', '12340'),
('400431', '0.5', '1', '2', '0', '12340'),
('400432', '0.5', '1', '2', '0', '12340'),
('400433', '0.5', '1', '2', '0', '12340'),
('400434', '0.5', '1', '2', '0', '12340'),
('400435', '0.5', '1', '2', '0', '12340'),
('400436', '0.5', '1', '2', '0', '12340'),
('400437', '0.5', '1', '2', '0', '12340'),
('400438', '0.5', '1', '2', '0', '12340'),
('400439', '0.5', '1', '2', '0', '12340'),
('400440', '0.5', '1', '2', '0', '12340'),
('400441', '0.5', '1', '2', '0', '12340'),
('400442', '0.5', '1', '2', '0', '12340'),
('400443', '0.5', '1', '2', '0', '12340'),
('400444', '0.5', '1', '2', '0', '12340'),
('400445', '0.5', '1', '2', '0', '12340'),
('400446', '0.5', '1', '2', '0', '12340'),
('400447', '0.5', '1', '2', '0', '12340'),
('400448', '0.5', '1', '2', '0', '12340'),
('400449', '0.5', '1', '2', '0', '12340'),
('400450', '0.5', '1', '2', '0', '12340'),
('400451', '0.5', '1', '2', '0', '12340'),
('400452', '0.5', '1', '2', '0', '12340'),
('400453', '0.5', '1', '2', '0', '12340'),
('400454', '0.5', '1', '2', '0', '12340'),
('400455', '0.5', '1', '2', '0', '12340'),
('400456', '0.5', '1', '2', '0', '12340'),
('400457', '0.5', '1', '2', '0', '12340'),
('400458', '0.5', '1', '2', '0', '12340'),
('400459', '0.5', '1', '2', '0', '12340'),
('400460', '0.5', '1', '2', '0', '12340'),
('400461', '0.5', '1', '2', '0', '12340'),
('400462', '0.5', '1', '2', '0', '12340'),
('400463', '0.5', '1', '2', '0', '12340'),
('400464', '0.5', '1', '2', '0', '12340'),
('400465', '0.5', '1', '2', '0', '12340'),
('400466', '0.5', '1', '2', '0', '12340'),
('400467', '0.5', '1', '2', '0', '12340'),
('400468', '0.5', '1', '2', '0', '12340'),
('400469', '0.5', '1', '2', '0', '12340'),
('400470', '0.5', '1', '2', '0', '12340'),
('400471', '0.5', '1', '2', '0', '12340'),
('400472', '0.5', '1', '2', '0', '12340'),
('400473', '0.5', '1', '2', '0', '12340'),
('400474', '0.5', '1', '2', '0', '12340'),
('400475', '0.5', '1', '2', '0', '12340'),
('400476', '0.5', '1', '2', '0', '12340'),
('400477', '0.5', '1', '2', '0', '12340'),
('400478', '0.5', '1', '2', '0', '12340'),
('400479', '0.5', '1', '2', '0', '12340'),
('400480', '0.5', '1', '2', '0', '12340'),
('400481', '0.5', '1', '2', '0', '12340'),
('400482', '0.5', '1', '2', '0', '12340'),
('400483', '0.5', '1', '2', '0', '12340'),
('400484', '0.5', '1', '2', '0', '12340'),
('400485', '0.5', '1', '2', '0', '12340'),
('400486', '0.5', '1', '2', '0', '12340'),
('400487', '0.5', '1', '2', '0', '12340'),
('400488', '0.5', '1', '2', '0', '12340'),
('400489', '0.5', '1', '2', '0', '12340'),
('400490', '0.5', '1', '2', '0', '12340'),
('400491', '0.5', '1', '2', '0', '12340'),
('400492', '0.5', '1', '2', '0', '12340'),
('400493', '0.5', '1', '2', '0', '12340'),
('400494', '0.5', '1', '2', '0', '12340'),
('400495', '0.5', '1', '2', '0', '12340'),
('400496', '0.5', '1', '2', '0', '12340'),
('400497', '0.5', '1', '2', '0', '12340'),
('400498', '0.5', '1', '2', '0', '12340'),
('400499', '0.5', '1', '2', '0', '12340'),
('400500', '0.5', '1', '2', '0', '12340'),
('400501', '0.5', '1', '2', '0', '12340'),
('400502', '0.5', '1', '2', '0', '12340'),
('400503', '0.5', '1', '2', '0', '12340'),
('400504', '0.5', '1', '2', '0', '12340'),
('400505', '0.5', '1', '2', '0', '12340'),
('400506', '0.5', '1', '2', '0', '12340'),
('400507', '0.5', '1', '2', '0', '12340'),
('400508', '0.5', '1', '2', '0', '12340'),
('400509', '0.5', '1', '2', '0', '12340'),
('400510', '0.5', '1', '2', '0', '12340'),
('400511', '0.5', '1', '2', '0', '12340'),
('400512', '0.5', '1', '2', '0', '12340'),
('400513', '0.5', '1', '2', '0', '12340'),
('400514', '0.5', '1', '2', '0', '12340'),
('400515', '0.5', '1', '2', '0', '12340'),
('400516', '0.5', '1', '2', '0', '12340'),
('400517', '0.5', '1', '2', '0', '12340'),
('400518', '0.5', '1', '2', '0', '12340'),
('400519', '0.5', '1', '2', '0', '12340'),
('400520', '0.5', '1', '2', '0', '12340'),
('400521', '0.5', '1', '2', '0', '12340'),
('400522', '0.5', '1', '2', '0', '12340'),
('400523', '0.5', '1', '2', '0', '12340'),
('400524', '0.5', '1', '2', '0', '12340'),
('400525', '0.5', '1', '2', '0', '12340'),
('400526', '0.5', '1', '2', '0', '12340'),
('400527', '0.5', '1', '2', '0', '12340'),
('400528', '0.5', '1', '2', '0', '12340'),
('400529', '0.5', '1', '2', '0', '12340'),
('400530', '0.5', '1', '2', '0', '12340'),
('400531', '0.5', '1', '2', '0', '12340'),
('400532', '0.5', '1', '2', '0', '12340'),
('400533', '0.5', '1', '2', '0', '12340'),
('400534', '0.5', '1', '2', '0', '12340'),
('400535', '0.5', '1', '2', '0', '12340'),
('400536', '0.5', '1', '2', '0', '12340'),
('400537', '0.5', '1', '2', '0', '12340'),
('400538', '0.5', '1', '2', '0', '12340'),
('400539', '0.5', '1', '2', '0', '12340'),
('400540', '0.5', '1', '2', '0', '12340'),
('400541', '0.5', '1', '2', '0', '12340'),
('400542', '0.5', '1', '2', '0', '12340'),
('400543', '0.5', '1', '2', '0', '12340'),
('400544', '0.5', '1', '2', '0', '12340'),
('400545', '0.5', '1', '2', '0', '12340'),
('400546', '0.5', '1', '2', '0', '12340'),
('400547', '0.5', '1', '2', '0', '12340'),
('400548', '0.5', '1', '2', '0', '12340'),
('400549', '0.5', '1', '2', '0', '12340'),
('400550', '0.5', '1', '2', '0', '12340'),
('400551', '0.5', '1', '2', '0', '12340'),
('400552', '0.5', '1', '2', '0', '12340'),
('400553', '0.5', '1', '2', '0', '12340'),
('400554', '0.5', '1', '2', '0', '12340'),
('400555', '0.5', '1', '2', '0', '12340'),
('400556', '0.5', '1', '2', '0', '12340'),
('400557', '0.5', '1', '2', '0', '12340'),
('400558', '0.5', '1', '2', '0', '12340'),
('400559', '0.5', '1', '2', '0', '12340'),
('400560', '0.5', '1', '2', '0', '12340'),
('400561', '0.5', '1', '2', '0', '12340'),
('400562', '0.5', '1', '2', '0', '12340'),
('400563', '0.5', '1', '2', '0', '12340'),
('400564', '0.5', '1', '2', '0', '12340'),
('400565', '0.5', '1', '2', '0', '12340'),
('400566', '0.5', '1', '2', '0', '12340'),
('400567', '0.5', '1', '2', '0', '12340'),
('400568', '0.5', '1', '2', '0', '12340'),
('400569', '0.5', '1', '2', '0', '12340'),
('400570', '0.5', '1', '2', '0', '12340'),
('400571', '0.5', '1', '2', '0', '12340'),
('400572', '0.5', '1', '2', '0', '12340'),
('400573', '0.5', '1', '2', '0', '12340'),
('400574', '0.5', '1', '2', '0', '12340'),
('400575', '0.5', '1', '2', '0', '12340'),
('400576', '0.5', '1', '2', '0', '12340'),
('400577', '0.5', '1', '2', '0', '12340'),
('400578', '0.5', '1', '2', '0', '12340'),
('400579', '0.5', '1', '2', '0', '12340'),
('400580', '0.5', '1', '2', '0', '12340'),
('400581', '0.5', '1', '2', '0', '12340'),
('400582', '0.5', '1', '2', '0', '12340'),
('400583', '0.5', '1', '2', '0', '12340'),
('400584', '0.5', '1', '2', '0', '12340'),
('400585', '0.5', '1', '2', '0', '12340'),
('400586', '0.5', '1', '2', '0', '12340'),
('400587', '0.5', '1', '2', '0', '12340'),
('400588', '0.5', '1', '2', '0', '12340'),
('400589', '0.5', '1', '2', '0', '12340'),
('400590', '0.5', '1', '2', '0', '12340'),
('400591', '0.5', '1', '2', '0', '12340'),
('400592', '0.5', '1', '2', '0', '12340'),
('400593', '0.5', '1', '2', '0', '12340'),
('400594', '0.5', '1', '2', '0', '12340'),
('400595', '0.5', '1', '2', '0', '12340'),
('400596', '0.5', '1', '2', '0', '12340'),
('400597', '0.5', '1', '2', '0', '12340'),
('400598', '0.5', '1', '2', '0', '12340'),
('400599', '0.5', '1', '2', '0', '12340'),
('400600', '0.5', '1', '2', '0', '12340'),
('400601', '0.5', '1', '2', '0', '12340'),
('400602', '0.5', '1', '2', '0', '12340'),
('400603', '0.5', '1', '2', '0', '12340'),
('400604', '0.5', '1', '2', '0', '12340'),
('400605', '0.5', '1', '2', '0', '12340'),
('400606', '0.5', '1', '2', '0', '12340'),
('400607', '0.5', '1', '2', '0', '12340'),
('400608', '0.5', '1', '2', '0', '12340'),
('400609', '0.5', '1', '2', '0', '12340'),
('400610', '0.5', '1', '2', '0', '12340'),
('400611', '0.5', '1', '2', '0', '12340'),
('400612', '0.5', '1', '2', '0', '12340'),
('400613', '0.5', '1', '2', '0', '12340'),
('400614', '0.5', '1', '2', '0', '12340'),
('400615', '0.5', '1', '2', '0', '12340'),
('400616', '0.5', '1', '2', '0', '12340'),
('400617', '0.5', '1', '2', '0', '12340'),
('400618', '0.5', '1', '2', '0', '12340'),
('400619', '0.5', '1', '2', '0', '12340'),
('400620', '0.5', '1', '2', '0', '12340'),
('400621', '0.5', '1', '2', '0', '12340'),
('400622', '0.5', '1', '2', '0', '12340'),
('400623', '0.5', '1', '2', '0', '12340'),
('400624', '0.5', '1', '2', '0', '12340'),
('400625', '0.5', '1', '2', '0', '12340'),
('400626', '0.5', '1', '2', '0', '12340'),
('400627', '0.5', '1', '2', '0', '12340'),
('400628', '0.5', '1', '2', '0', '12340'),
('400629', '0.5', '1', '2', '0', '12340'),
('400630', '0.5', '1', '2', '0', '12340'),
('400631', '0.5', '1', '2', '0', '12340'),
('400632', '0.5', '1', '2', '0', '12340'),
('400633', '0.5', '1', '2', '0', '12340'),
('400634', '0.5', '1', '2', '0', '12340'),
('400635', '0.5', '1', '2', '0', '12340'),
('400636', '0.5', '1', '2', '0', '12340'),
('400637', '0.5', '1', '2', '0', '12340'),
('400638', '0.5', '1', '2', '0', '12340'),
('400639', '0.5', '1', '2', '0', '12340'),
('400640', '0.5', '1', '2', '0', '12340'),
('400641', '0.5', '1', '2', '0', '12340'),
('400642', '0.5', '1', '2', '0', '12340'),
('400643', '0.5', '1', '2', '0', '12340'),
('400644', '0.5', '1', '2', '0', '12340'),
('400645', '0.5', '1', '2', '0', '12340'),
('400646', '0.5', '1', '2', '0', '12340'),
('400647', '0.5', '1', '2', '0', '12340'),
('400648', '0.5', '1', '2', '0', '12340'),
('400649', '0.5', '1', '2', '0', '12340'),
('400650', '0.5', '1', '2', '0', '12340'),
('400651', '0.5', '1', '2', '0', '12340'),
('400652', '0.5', '1', '2', '0', '12340'),
('400653', '0.5', '1', '2', '0', '12340'),
('400654', '0.5', '1', '2', '0', '12340'),
('400655', '0.5', '1', '2', '0', '12340'),
('400656', '0.5', '1', '2', '0', '12340'),
('400657', '0.5', '1', '2', '0', '12340'),
('400658', '0.5', '1', '2', '0', '12340'),
('400659', '0.5', '1', '2', '0', '12340'),
('400660', '0.5', '1', '2', '0', '12340'),
('400661', '0.5', '1', '2', '0', '12340'),
('400662', '0.5', '1', '2', '0', '12340'),
('400663', '0.5', '1', '2', '0', '12340'),
('400664', '0.5', '1', '2', '0', '12340'),
('400665', '0.5', '1', '2', '0', '12340'),
('400666', '0.5', '1', '2', '0', '12340'),
('400667', '0.5', '1', '2', '0', '12340'),
('400668', '0.5', '1', '2', '0', '12340'),
('400669', '0.5', '1', '2', '0', '12340'),
('400670', '0.5', '1', '2', '0', '12340'),
('400671', '0.5', '1', '2', '0', '12340'),
('400672', '0.5', '1', '2', '0', '12340'),
('400673', '0.5', '1', '2', '0', '12340'),
('400674', '0.5', '1', '2', '0', '12340'),
('400675', '0.5', '1', '2', '0', '12340'),
('400676', '0.5', '1', '2', '0', '12340'),
('400677', '0.5', '1', '2', '0', '12340'),
('400678', '0.5', '1', '2', '0', '12340'),
('400679', '0.5', '1', '2', '0', '12340'),
('400680', '0.5', '1', '2', '0', '12340'),
('400681', '0.5', '1', '2', '0', '12340'),
('400682', '0.5', '1', '2', '0', '12340'),
('400683', '0.5', '1', '2', '0', '12340'),
('400684', '0.5', '1', '2', '0', '12340'),
('400685', '0.5', '1', '2', '0', '12340'),
('400686', '0.5', '1', '2', '0', '12340'),
('400687', '0.5', '1', '2', '0', '12340'),
('400688', '0.5', '1', '2', '0', '12340'),
('400689', '0.5', '1', '2', '0', '12340'),
('400690', '0.5', '1', '2', '0', '12340'),
('400691', '0.5', '1', '2', '0', '12340'),
('400692', '0.5', '1', '2', '0', '12340'),
('400693', '0.5', '1', '2', '0', '12340'),
('400694', '0.5', '1', '2', '0', '12340'),
('400695', '0.5', '1', '2', '0', '12340'),
('400696', '0.5', '1', '2', '0', '12340'),
('400697', '0.5', '1', '2', '0', '12340'),
('400698', '0.5', '1', '2', '0', '12340'),
('400699', '0.5', '1', '2', '0', '12340'),
('400700', '0.5', '1', '2', '0', '12340'),
('400701', '0.5', '1', '2', '0', '12340'),
('400702', '0.5', '1', '2', '0', '12340'),
('400703', '0.5', '1', '2', '0', '12340'),
('400704', '0.5', '1', '2', '0', '12340'),
('400705', '0.5', '1', '2', '0', '12340'),
('400706', '0.5', '1', '2', '0', '12340'),
('400707', '0.5', '1', '2', '0', '12340'),
('400708', '0.5', '1', '2', '0', '12340'),
('400709', '0.5', '1', '2', '0', '12340'),
('400710', '0.5', '1', '2', '0', '12340'),
('400711', '0.5', '1', '2', '0', '12340'),
('400712', '0.5', '1', '2', '0', '12340'),
('400713', '0.5', '1', '2', '0', '12340'),
('400714', '0.5', '1', '2', '0', '12340'),
('400715', '0.5', '1', '2', '0', '12340'),
('400716', '0.5', '1', '2', '0', '12340'),
('400717', '0.5', '1', '2', '0', '12340'),
('400718', '0.5', '1', '2', '0', '12340'),
('400719', '0.5', '1', '2', '0', '12340'),
('400720', '0.5', '1', '2', '0', '12340'),
('400721', '0.5', '1', '2', '0', '12340'),
('400722', '0.5', '1', '2', '0', '12340'),
('400723', '0.5', '1', '2', '0', '12340'),
('400724', '0.5', '1', '2', '0', '12340'),
('400725', '0.5', '1', '2', '0', '12340'),
('400726', '0.5', '1', '2', '0', '12340'),
('400727', '0.5', '1', '2', '0', '12340'),
('400728', '0.5', '1', '2', '0', '12340'),
('400729', '0.5', '1', '2', '0', '12340'),
('400730', '0.5', '1', '2', '0', '12340'),
('400731', '0.5', '1', '2', '0', '12340'),
('400732', '0.5', '1', '2', '0', '12340'),
('400733', '0.5', '1', '2', '0', '12340'),
('400734', '0.5', '1', '2', '0', '12340'),
('400735', '0.5', '1', '2', '0', '12340'),
('400736', '0.5', '1', '2', '0', '12340'),
('400737', '0.5', '1', '2', '0', '12340'),
('400738', '0.5', '1', '2', '0', '12340'),
('400739', '0.5', '1', '2', '0', '12340'),
('400740', '0.5', '1', '2', '0', '12340'),
('400741', '0.5', '1', '2', '0', '12340'),
('400742', '0.5', '1', '2', '0', '12340'),
('400743', '0.5', '1', '2', '0', '12340'),
('400744', '0.5', '1', '2', '0', '12340'),
('400745', '0.5', '1', '2', '0', '12340'),
('400746', '0.5', '1', '2', '0', '12340'),
('400747', '0.5', '1', '2', '0', '12340'),
('400748', '0.5', '1', '2', '0', '12340'),
('400749', '0.5', '1', '2', '0', '12340'),
('400750', '0.5', '1', '2', '0', '12340'),
('400751', '0.5', '1', '2', '0', '12340'),
('400752', '0.5', '1', '2', '0', '12340'),
('400753', '0.5', '1', '2', '0', '12340'),
('400754', '0.5', '1', '2', '0', '12340'),
('400755', '0.5', '1', '2', '0', '12340'),
('400756', '0.5', '1', '2', '0', '12340'),
('400757', '0.5', '1', '2', '0', '12340'),
('400758', '0.5', '1', '2', '0', '12340'),
('400759', '0.5', '1', '2', '0', '12340'),
('400760', '0.5', '1', '2', '0', '12340'),
('400761', '0.5', '1', '2', '0', '12340'),
('400762', '0.5', '1', '2', '0', '12340'),
('400763', '0.5', '1', '2', '0', '12340'),
('400764', '0.5', '1', '2', '0', '12340'),
('400765', '0.5', '1', '2', '0', '12340'),
('400766', '0.5', '1', '2', '0', '12340'),
('400767', '0.5', '1', '2', '0', '12340'),
('400768', '0.5', '1', '2', '0', '12340'),
('400769', '0.5', '1', '2', '0', '12340'),
('400770', '0.5', '1', '2', '0', '12340'),
('400771', '0.5', '1', '2', '0', '12340'),
('400772', '0.5', '1', '2', '0', '12340'),
('400773', '0.5', '1', '2', '0', '12340'),
('400774', '0.5', '1', '2', '0', '12340'),
('400775', '0.5', '1', '2', '0', '12340'),
('400776', '0.5', '1', '2', '0', '12340'),
('400777', '0.5', '1', '2', '0', '12340'),
('400778', '0.5', '1', '2', '0', '12340'),
('400779', '0.5', '1', '2', '0', '12340'),
('400780', '0.5', '1', '2', '0', '12340'),
('400781', '0.5', '1', '2', '0', '12340'),
('400782', '0.5', '1', '2', '0', '12340'),
('400783', '0.5', '1', '2', '0', '12340'),
('400784', '0.5', '1', '2', '0', '12340'),
('400785', '0.5', '1', '2', '0', '12340'),
('400786', '0.5', '1', '2', '0', '12340'),
('400787', '0.5', '1', '2', '0', '12340'),
('400788', '0.5', '1', '2', '0', '12340'),
('400789', '0.5', '1', '2', '0', '12340'),
('400790', '0.5', '1', '2', '0', '12340'),
('400791', '0.5', '1', '2', '0', '12340'),
('400792', '0.5', '1', '2', '0', '12340'),
('400793', '0.5', '1', '2', '0', '12340'),
('400794', '0.5', '1', '2', '0', '12340'),
('400795', '0.5', '1', '2', '0', '12340'),
('400796', '0.5', '1', '2', '0', '12340'),
('400797', '0.5', '1', '2', '0', '12340'),
('400798', '0.5', '1', '2', '0', '12340'),
('400799', '0.5', '1', '2', '0', '12340'),
('400800', '0.5', '1', '2', '0', '12340'),
('400801', '0.5', '1', '2', '0', '12340'),
('400802', '0.5', '1', '2', '0', '12340'),
('400803', '0.5', '1', '2', '0', '12340'),
('400804', '0.5', '1', '2', '0', '12340'),
('400805', '0.5', '1', '2', '0', '12340'),
('400806', '0.5', '1', '2', '0', '12340'),
('400807', '0.5', '1', '2', '0', '12340'),
('400808', '0.5', '1', '2', '0', '12340'),
('400809', '0.5', '1', '2', '0', '12340'),
('400810', '0.5', '1', '2', '0', '12340'),
('400811', '0.5', '1', '2', '0', '12340'),
('400812', '0.5', '1', '2', '0', '12340'),
('400813', '0.5', '1', '2', '0', '12340'),
('400814', '0.5', '1', '2', '0', '12340'),
('400815', '0.5', '1', '2', '0', '12340'),
('400816', '0.5', '1', '2', '0', '12340'),
('400817', '0.5', '1', '2', '0', '12340'),
('400818', '0.5', '1', '2', '0', '12340'),
('400819', '0.5', '1', '2', '0', '12340'),
('400820', '0.5', '1', '2', '0', '12340'),
('400821', '0.5', '1', '2', '0', '12340'),
('400822', '0.5', '1', '2', '0', '12340'),
('400823', '0.5', '1', '2', '0', '12340'),
('400824', '0.5', '1', '2', '0', '12340'),
('400825', '0.5', '1', '2', '0', '12340'),
('400826', '0.5', '1', '2', '0', '12340'),
('400827', '0.5', '1', '2', '0', '12340'),
('400828', '0.5', '1', '2', '0', '12340'),
('400829', '0.5', '1', '2', '0', '12340'),
('400830', '0.5', '1', '2', '0', '12340'),
('400831', '0.5', '1', '2', '0', '12340'),
('400832', '0.5', '1', '2', '0', '12340'),
('400833', '0.5', '1', '2', '0', '12340'),
('400834', '0.5', '1', '2', '0', '12340'),
('400835', '0.5', '1', '2', '0', '12340'),
('400836', '0.5', '1', '2', '0', '12340'),
('400837', '0.5', '1', '2', '0', '12340'),
('400838', '0.5', '1', '2', '0', '12340'),
('400839', '0.5', '1', '2', '0', '12340'),
('400840', '0.5', '1', '2', '0', '12340'),
('400841', '0.5', '1', '2', '0', '12340'),
('400842', '0.5', '1', '2', '0', '12340'),
('400843', '0.5', '1', '2', '0', '12340'),
('400844', '0.5', '1', '2', '0', '12340'),
('400845', '0.5', '1', '2', '0', '12340'),
('400846', '0.5', '1', '2', '0', '12340'),
('400847', '0.5', '1', '2', '0', '12340'),
('400848', '0.5', '1', '2', '0', '12340'),
('400849', '0.5', '1', '2', '0', '12340'),
('400850', '0.5', '1', '2', '0', '12340'),
('400851', '0.5', '1', '2', '0', '12340'),
('400852', '0.5', '1', '2', '0', '12340'),
('400853', '0.5', '1', '2', '0', '12340'),
('400854', '0.5', '1', '2', '0', '12340'),
('400855', '0.5', '1', '2', '0', '12340'),
('400856', '0.5', '1', '2', '0', '12340'),
('400857', '0.5', '1', '2', '0', '12340'),
('400858', '0.5', '1', '2', '0', '12340'),
('400859', '0.5', '1', '2', '0', '12340'),
('400860', '0.5', '1', '2', '0', '12340'),
('400861', '0.5', '1', '2', '0', '12340'),
('400862', '0.5', '1', '2', '0', '12340'),
('400863', '0.5', '1', '2', '0', '12340'),
('400864', '0.5', '1', '2', '0', '12340'),
('400865', '0.5', '1', '2', '0', '12340'),
('400866', '0.5', '1', '2', '0', '12340'),
('400867', '0.5', '1', '2', '0', '12340'),
('400868', '0.5', '1', '2', '0', '12340'),
('400869', '0.5', '1', '2', '0', '12340'),
('400870', '0.5', '1', '2', '0', '12340'),
('400871', '0.5', '1', '2', '0', '12340'),
('400872', '0.5', '1', '2', '0', '12340'),
('400873', '0.5', '1', '2', '0', '12340'),
('400874', '0.5', '1', '2', '0', '12340'),
('400875', '0.5', '1', '2', '0', '12340'),
('400876', '0.5', '1', '2', '0', '12340'),
('400877', '0.5', '1', '2', '0', '12340'),
('400878', '0.5', '1', '2', '0', '12340'),
('400879', '0.5', '1', '2', '0', '12340'),
('400880', '0.5', '1', '2', '0', '12340'),
('400881', '0.5', '1', '2', '0', '12340'),
('400882', '0.5', '1', '2', '0', '12340'),
('400883', '0.5', '1', '2', '0', '12340'),
('400884', '0.5', '1', '2', '0', '12340'),
('400885', '0.5', '1', '2', '0', '12340'),
('400886', '0.5', '1', '2', '0', '12340'),
('400887', '0.5', '1', '2', '0', '12340'),
('400888', '0.5', '1', '2', '0', '12340'),
('400889', '0.5', '1', '2', '0', '12340'),
('400890', '0.5', '1', '2', '0', '12340'),
('400891', '0.5', '1', '2', '0', '12340'),
('400892', '0.5', '1', '2', '0', '12340'),
('400893', '0.5', '1', '2', '0', '12340'),
('400894', '0.5', '1', '2', '0', '12340'),
('400895', '0.5', '1', '2', '0', '12340'),
('400896', '0.5', '1', '2', '0', '12340'),
('400897', '0.5', '1', '2', '0', '12340'),
('400898', '0.5', '1', '2', '0', '12340'),
('400899', '0.5', '1', '2', '0', '12340'),
('400900', '0.5', '1', '2', '0', '12340'),
('400901', '0.5', '1', '2', '0', '12340'),
('400902', '0.5', '1', '2', '0', '12340'),
('400903', '0.5', '1', '2', '0', '12340'),
('400904', '0.5', '1', '2', '0', '12340'),
('400905', '0.5', '1', '2', '0', '12340'),
('400906', '0.5', '1', '2', '0', '12340'),
('400907', '0.5', '1', '2', '0', '12340'),
('400908', '0.5', '1', '2', '0', '12340'),
('400909', '0.5', '1', '2', '0', '12340'),
('400910', '0.5', '1', '2', '0', '12340'),
('400911', '0.5', '1', '2', '0', '12340'),
('400912', '0.5', '1', '2', '0', '12340'),
('400913', '0.5', '1', '2', '0', '12340'),
('400914', '0.5', '1', '2', '0', '12340'),
('400915', '0.5', '1', '2', '0', '12340'),
('400916', '0.5', '1', '2', '0', '12340'),
('400917', '0.5', '1', '2', '0', '12340'),
('400918', '0.5', '1', '2', '0', '12340'),
('400919', '0.5', '1', '2', '0', '12340'),
('400920', '0.5', '1', '2', '0', '12340'),
('400921', '0.5', '1', '2', '0', '12340'),
('400922', '0.5', '1', '2', '0', '12340'),
('400923', '0.5', '1', '2', '0', '12340'),
('400924', '0.5', '1', '2', '0', '12340'),
('400925', '0.5', '1', '2', '0', '12340'),
('400926', '0.5', '1', '2', '0', '12340'),
('400927', '0.5', '1', '2', '0', '12340'),
('400928', '0.5', '1', '2', '0', '12340'),
('400929', '0.5', '1', '2', '0', '12340'),
('400930', '0.5', '1', '2', '0', '12340'),
('400931', '0.5', '1', '2', '0', '12340'),
('400932', '0.5', '1', '2', '0', '12340'),
('400933', '0.5', '1', '2', '0', '12340'),
('400934', '0.5', '1', '2', '0', '12340'),
('400935', '0.5', '1', '2', '0', '12340'),
('400936', '0.5', '1', '2', '0', '12340'),
('400937', '0.5', '1', '2', '0', '12340'),
('400938', '0.5', '1', '2', '0', '12340'),
('400939', '0.5', '1', '2', '0', '12340'),
('400940', '0.5', '1', '2', '0', '12340'),
('400941', '0.5', '1', '2', '0', '12340'),
('400942', '0.5', '1', '2', '0', '12340'),
('400943', '0.5', '1', '2', '0', '12340'),
('400944', '0.5', '1', '2', '0', '12340'),
('400945', '0.5', '1', '2', '0', '12340'),
('400946', '0.5', '1', '2', '0', '12340'),
('400947', '0.5', '1', '2', '0', '12340'),
('400948', '0.5', '1', '2', '0', '12340'),
('400949', '0.5', '1', '2', '0', '12340'),
('400950', '0.5', '1', '2', '0', '12340'),
('400951', '0.5', '1', '2', '0', '12340'),
('400952', '0.5', '1', '2', '0', '12340'),
('400953', '0.5', '1', '2', '0', '12340'),
('400954', '0.5', '1', '2', '0', '12340'),
('400955', '0.5', '1', '2', '0', '12340'),
('400956', '0.5', '1', '2', '0', '12340'),
('400957', '0.5', '1', '2', '0', '12340'),
('400958', '0.5', '1', '2', '0', '12340'),
('400959', '0.5', '1', '2', '0', '12340'),
('400960', '0.5', '1', '2', '0', '12340'),
('400961', '0.5', '1', '2', '0', '12340'),
('400962', '0.5', '1', '2', '0', '12340'),
('400963', '0.5', '1', '2', '0', '12340'),
('400964', '0.5', '1', '2', '0', '12340'),
('400965', '0.5', '1', '2', '0', '12340'),
('400966', '0.5', '1', '2', '0', '12340'),
('400967', '0.5', '1', '2', '0', '12340'),
('400968', '0.5', '1', '2', '0', '12340'),
('400969', '0.5', '1', '2', '0', '12340'),
('400970', '0.5', '1', '2', '0', '12340'),
('400971', '0.5', '1', '2', '0', '12340'),
('400972', '0.5', '1', '2', '0', '12340'),
('400973', '0.5', '1', '2', '0', '12340'),
('400974', '0.5', '1', '2', '0', '12340'),
('400975', '0.5', '1', '2', '0', '12340'),
('400976', '0.5', '1', '2', '0', '12340'),
('400977', '0.5', '1', '2', '0', '12340'),
('400978', '0.5', '1', '2', '0', '12340'),
('400979', '0.5', '1', '2', '0', '12340');

COMMIT;
DROP PROCEDURE `bm3d_templates`;
DROP TEMPORARY TABLE `bm3d_creature`, `bm3d_forms`, `bm3d_species`;
CREATE TABLE IF NOT EXISTS `battlemon_3d_removed_spawns` LIKE `creature`;
START TRANSACTION;
INSERT IGNORE INTO `battlemon_3d_removed_spawns` SELECT `c`.* FROM `creature` `c` JOIN `creature_template` `t` ON `c`.`id`=`t`.`entry` WHERE `t`.`ScriptName`='npc_battlemon_overworld' AND `t`.`entry` IN (1000045,1000046,1000047,1000048,1000049,1000050,1000051,1000052,1000053,1000072,1000124,1000250,1000259,1000383,1000554,1000557,1000611,1000682,1000688,1000733,1000748,1000784,1000817,1000834,1000858,1000914,1000936,1000966,1000967,1000980,1000984,1000989,1001019,1001032,1001045,1001049,1001050,1001051,1001055,1001056,1001067,1001070,1001073,1001084,1001096,1001097,1001098,1001100,1001101,1001102,1001115,1001116,1001142,1001177,1001215,1001244,1001245,1001253,1001382,1001406,1001409,1001415,1001485,1001505,1001516,1001517,1001518,1001540,1001553,1001564,1001565,1001566,1001567,1001568,1001569,1001570,1001571);
DELETE `c` FROM `creature` `c` JOIN `battlemon_3d_removed_spawns` `b` ON `c`.`guid`=`b`.`guid` AND `c`.`id`=`b`.`id` JOIN `creature_template` `t` ON `c`.`id`=`t`.`entry` WHERE `t`.`ScriptName`='npc_battlemon_overworld' AND `t`.`entry` IN (1000045,1000046,1000047,1000048,1000049,1000050,1000051,1000052,1000053,1000072,1000124,1000250,1000259,1000383,1000554,1000557,1000611,1000682,1000688,1000733,1000748,1000784,1000817,1000834,1000858,1000914,1000936,1000966,1000967,1000980,1000984,1000989,1001019,1001032,1001045,1001049,1001050,1001051,1001055,1001056,1001067,1001070,1001073,1001084,1001096,1001097,1001098,1001100,1001101,1001102,1001115,1001116,1001142,1001177,1001215,1001244,1001245,1001253,1001382,1001406,1001409,1001415,1001485,1001505,1001516,1001517,1001518,1001540,1001553,1001564,1001565,1001566,1001567,1001568,1001569,1001570,1001571);
COMMIT;
