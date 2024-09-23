let map;
let deckInstance;
let cacheId = null;
let debounceTimer;
let allLayers = {
    'coverage-area': null,
    'stops': null,
    'population': null,
    'clusters': null
};
let hidingLayers = {
    'coverage-area': null,
    'stops': null,
    'population': null,
    'clusters': null
};


document.addEventListener('DOMContentLoaded', function () {
    const bufferSlider = document.getElementById('buffer-slider');
    const bufferValue = document.getElementById('buffer-value');
    
    const clusterSlider = document.getElementById('cluster-slider');
    const clusterValue = document.getElementById('cluster-value');

    let animationFrameId;

    // Função de debounce
    function debounce(func, delay) {
        return function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => func.apply(this, arguments), delay);
        };
    }

    // Função para atualizar o buffer
    const updateBuffer = debounce(async function (value) {
        console.log("Buffer selecionado:", value);

        try {
            if (isNaN(value)) {
                errorsDiv.textContent = 'O valor do buffer deve ser um número inteiro.';
                return;
            }

            if (!cacheId) {
                errorsDiv.textContent = 'Cache ID não disponível. Por favor, processe os dados primeiro.';
                return;
            }

            const bufferResponse = await fetch('/new_buffer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cache_id: cacheId,
                    buffer: parseInt(value)
                })
            });

            if (bufferResponse.ok) {
                const bufferResult = await bufferResponse.json();

                if (bufferResult.status === 'success') {
                    updateMap(bufferResult);
                } else {
                    errorsDiv.innerHTML = bufferResult.message || 'Erro desconhecido ocorreu.';
                }
            } else {
                errorsDiv.textContent = 'Erro na requisição do buffer.';
            }
        } catch (bufferError) {
            errorsDiv.textContent = 'Ocorreu um erro durante o processamento do buffer.';
            console.error(bufferError);
        }
    }, 300); // 300ms de delay

    // Função para atualizar o valor e posição do texto abaixo do thumb
    function updateSliderValue(slider, valueElement, sliderWidth) {
        const min = slider.min;
        const max = slider.max;
        const value = slider.value;

        const percent = (value - min) / (max - min);
        const offset = percent * (sliderWidth - 16);

        valueElement.textContent = value;
        valueElement.style.left = `${offset}px`;
    }

    // Função que irá ser chamada pelo requestAnimationFrame
    function animateSliderUpdate(slider, valueElement, sliderWidth) {
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
        }
        animationFrameId = requestAnimationFrame(function () {
            updateSliderValue(slider, valueElement, sliderWidth);
        });
    }

    // Adiciona os eventos de input para o buffer e o cluster
    bufferSlider.addEventListener('input', function () {
        const sliderWidth = bufferSlider.offsetWidth;
        animateSliderUpdate(bufferSlider, bufferValue, sliderWidth);
    });

    clusterSlider.addEventListener('input', function () {
        const sliderWidth = clusterSlider.offsetWidth;
        animateSliderUpdate(clusterSlider, clusterValue, sliderWidth);
    });

    // Envia o request apenas quando o usuário soltar o mouse
    bufferSlider.addEventListener('change', function () {
        updateBuffer(bufferSlider.value);
    });

    // Inicializa os valores e posições ao carregar a página
    updateSliderValue(bufferSlider, bufferValue, bufferSlider.offsetWidth);
    updateSliderValue(clusterSlider, clusterValue, clusterSlider.offsetWidth);

    initMap();

    const form = document.getElementById('data-form');
    const errorsDiv = document.getElementById('errors');
    const uploadFormDiv = document.getElementById('upload-form');
    const legendDiv = document.getElementById('legend');
    const slidersDiv = document.getElementById('slider-container');
    const layerControlDiv = document.getElementById('layer-control');

    // Controle de Camadas - selecione os checkboxes
    let coverageAreaCheckbox = document.getElementById('coverage-area-layer');
    let stopsCheckbox = document.getElementById('stops-layer');
    let populationCheckbox = document.getElementById('population-layer');
    let clustersCheckbox = document.getElementById('clusters-layer');

    function updateLayerVisibility() {
        const layersToDisplay = [];
    
        // Adiciona as camadas com base no estado dos checkboxes
        if (coverageAreaCheckbox.checked && allLayers['coverage-area']) {
            layersToDisplay.push(allLayers['coverage-area']);
        }
    
        if (stopsCheckbox.checked && allLayers['stops']) {
            layersToDisplay.push(allLayers['stops']);
        }
    
        if (populationCheckbox.checked && allLayers['population']) {
            layersToDisplay.push(allLayers['population']);
        }
    
        if (clustersCheckbox.checked && allLayers['clusters']) {
            layersToDisplay.push(allLayers['clusters']);
        }
    
        // Atualiza o deckInstance com as camadas a serem exibidas
        deckInstance.setProps({
            layers: layersToDisplay
        });
    
        console.log("Camadas a serem exibidas:", layersToDisplay.map(layer => layer.id));
    }
    

    // Adiciona eventos aos checkboxes se eles existirem
    if (coverageAreaCheckbox && stopsCheckbox && populationCheckbox && clustersCheckbox) {
        coverageAreaCheckbox.addEventListener('change', updateLayerVisibility);
        stopsCheckbox.addEventListener('change', updateLayerVisibility);
        populationCheckbox.addEventListener('change', updateLayerVisibility);
        clustersCheckbox.addEventListener('change', updateLayerVisibility);
    }

    // Listener para a submissão do formulário
    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        errorsDiv.innerHTML = '';

        const gtfsFileInput = document.getElementById('gtfsFile');
        const populationFileInput = document.getElementById('populationFile');

        const gtfsFile = gtfsFileInput.files[0];
        const populationFile = populationFileInput.files[0];

        if (!gtfsFile || !populationFile) {
            errorsDiv.textContent = 'Por favor, selecione ambos os arquivos.';
            return;
        }

        const formData = new FormData();
        formData.append('gtfsFile', gtfsFile);
        formData.append('populationFile', populationFile);

        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.status === 'success') {
                uploadFormDiv.style.display = 'none';
                updateMap(result);
                legendDiv.classList.remove('hidden');
                slidersDiv.classList.remove('hidden');
                layerControlDiv.classList.remove('hidden');
                toggleLayerControlButton.classList.remove('hidden'); // Mostra o botão
                cacheId = result.request_id;
            } else {
                errorsDiv.innerHTML = result.errors.join('<br>');
            }
        } catch (error) {
            errorsDiv.textContent = 'Ocorreu um erro durante o processamento.';
            console.error(error);
        }
    });

    // Botão para mostrar/ocultar controle de camadas
    const toggleLayerControlButton = document.getElementById('toggle-layer-control');
    if (toggleLayerControlButton) {
        toggleLayerControlButton.addEventListener('click', function () {
            layerControlDiv.classList.toggle('hidden');
        });
    } else {
        console.warn("'toggle-layer-control' button not found in the DOM.");
    }
});


function initMap() {
    map = new maplibregl.Map({
        container: 'map',
        style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        center: [-9.1393, 38.7223], // Lisboa
        zoom: 12,
        pitch: 0,
        bearing: 0
    });

    // Adicione o canvas antes de instanciar o deck
    const deckCanvas = document.createElement('canvas');
    deckCanvas.id = 'deck-canvas';
    map.getCanvasContainer().appendChild(deckCanvas);

    // Configure o deckInstance
    deckInstance = new deck.Deck({
        canvas: 'deck-canvas',
        width: '100%',
        height: '100%',
        initialViewState: {
            longitude: -9.1393,
            latitude: 38.7223,
            zoom: 12,
            pitch: 0,
            bearing: 0
        },
        controller: false,
        layers: []
    });

    // Sincronize o deckInstance apenas quando a movimentação termina
    map.on('move', () => {
        const { lng, lat } = map.getCenter();
        deckInstance.setProps({
            viewState: {
                longitude: lng,
                latitude: lat,
                zoom: map.getZoom(),
                pitch: map.getPitch(),
                bearing: map.getBearing()
            }
        });
    });
}

function updateMap(data) {
    try {
        console.log("Dados recebidos:", data);

        const stops = data.stops;
        const coverageArea = data.coverage_area;
        const population = data.population;

        // Encontrar o ponto de maior população
        const maxPopFeature = population.features.reduce((max, feature) => {
            return feature.properties.number_of_people > (max.properties.number_of_people || 0)
                ? feature
                : max;
        }, { properties: { number_of_people: 0 }, geometry: { coordinates: [0, 0] } });

        const newLongitude = maxPopFeature.geometry.coordinates[0];
        const newLatitude = maxPopFeature.geometry.coordinates[1];

        // Atualizar o mapa MapLibre com uma transição suave
        map.flyTo({
            center: [newLongitude, newLatitude],
            zoom: 12,
            pitch: 0,
            bearing: 0,
            duration: 500 // Duração reduzida
        });

        // Criar camadas de dados
        const dataLayers = createLayers(stops, coverageArea, population);

        // Atualizar as camadas no deck.gl
        deckInstance.setProps({
            layers: dataLayers
        });

        // Após atualizar as camadas, re-apply a visibilidade baseada nos checkboxes
        const layerControlDiv = document.getElementById('layer-control');
        if (!layerControlDiv.classList.contains('hidden')) {
            updateLayerVisibility();
        }

    } catch (error) {
        const errorsDiv = document.getElementById('errors');
        errorsDiv.textContent = 'Ocorreu um erro durante a atualização do mapa.';
        console.error('Erro em updateMap:', error);
    }
}

function createLayers(stops, coverageArea, population) {
    // Camada de Paradas usando ScatterplotLayer
    allLayers['stops'] = new deck.ScatterplotLayer({
        id: 'stops',
        data: stops.features,
        getPosition: f => f.geometry.coordinates,
        getRadius: 9,
        radiusMinPixels: 7,
        getFillColor: [0, 0, 255],
        pickable: true
    });

    // Camada de Área de Cobertura
    allLayers['coverage-area'] = new deck.GeoJsonLayer({
        id: 'coverage-area',
        data: coverageArea,
        filled: true,
        stroked: false,
        getFillColor: [0, 0, 255, 50]
    });

    // Camada de População usando ScatterplotLayer
    allLayers['population'] = new deck.ScatterplotLayer({
        id: 'population',
        data: population.features,
        getPosition: f => f.geometry.coordinates,
        getRadius: 5,
        radiusMinPixels: 3,
        getFillColor: f => {
            if (f.properties.covered === 'Covered') {
                return [0, 255, 0]; // Verde
            } else if (f.properties.covered === 'Not Covered') {
                return [255, 0, 0]; // Vermelho
            } else {
                return [128, 128, 128]; // Cinza para casos indefinidos
            }
        },
        pickable: true
    });

    return [allLayers['coverage-area'], allLayers['stops'], allLayers['population']];
}

document.getElementById('generate-clusters').addEventListener('click', async function () {
    // Certifique-se de que o cacheId está disponível
    if (!cacheId) {
        errorsDiv.textContent = 'Cache ID não disponível. Por favor, processe os dados primeiro.';
        return;
    }

    try {
        // Seleciona o elemento DOM para exibir mensagens de erro
        const errorsDiv = document.getElementById('errorsDiv');
        const coverage = document.getElementById('buffer-slider');
        const minpop = document.getElementById('cluster-slider');
        const response = await fetch(`/generate_clusters?cache_id=${cacheId}&coverage=${coverage.value}&minpop=${minpop.value}`);

        if (response.ok) {
            const clusterData = await response.json();
            console.log("Dados de cluster recebidos:", clusterData);
            if (clusterData) {
                // Assumindo que clusterData.data contém o GeoJSON
                allLayers['clustersLayer'] = new deck.GeoJsonLayer({
                    id: 'clusters',
                    data: clusterData,
                    filled: true,
                    stroked: false,
                    getFillColor: [255, 255, 0, 85]
                });
        
                // Remover a camada de clusters existente, se houver
                const existingLayers = deckInstance.props.layers.filter(layer => layer.id !== 'clusters');
        
                // Adicionar a nova camada de clusters
                deckInstance.setProps({
                    layers: [...existingLayers, allLayers['clustersLayer']]
                });

                // Atualizar o controle de camadas para incluir a nova camada
                const clustersCheckbox = document.getElementById('clusters-layer');
                if (!clustersCheckbox) {
                    // Se o checkbox não existe, crie-o
                    const layerControlDiv = document.getElementById('layer-control');
                    const layerItem = document.createElement('div');
                    layerItem.className = 'layer-item';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.id = 'clusters-layer';
                    checkbox.checked = true;

                    const label = document.createElement('label');
                    label.htmlFor = 'clusters-layer';
                    label.textContent = 'Clusters de População Não Coberta';

                    layerItem.appendChild(checkbox);
                    layerItem.appendChild(label);
                    layerControlDiv.appendChild(layerItem);

                    // Adiciona evento para o novo checkbox
                    checkbox.addEventListener('change', updateLayerVisibility);
                }

                console.log("Clusters gerados e adicionados ao mapa.");
            } else {
                errorsDiv.textContent = 'Dados de cluster inválidos recebidos do servidor.';
            }
        } else {
            errorsDiv.textContent = 'Erro na requisição para gerar clusters.';
        }
    } catch (error) {
        errorsDiv.textContent = 'Ocorreu um erro durante o processamento dos clusters.';
        console.error('Erro ao gerar clusters:', error);
    }
});
